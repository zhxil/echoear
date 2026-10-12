"""Check built partition bytes, payload sizes, flash addresses and resource hashes."""
from pathlib import Path
import hashlib
import json
import struct

root=Path(__file__).resolve().parents[1]
build=root/'build'
data=(build/'partition_table/partition-table.bin').read_bytes()
parts={}
for offset in range(0,len(data),32):
    magic,kind,subtype,start,size,name,flags=struct.unpack('<HBBII16sI',data[offset:offset+32])
    if magic!=0x50AA: break
    name=name.split(b'\0')[0].decode()
    parts[name]={'offset':start,'size':size,'type':kind,'subtype':subtype}
ordered=sorted(parts.items(),key=lambda item:item[1]['offset'])
end=0x9000
for name,part in ordered:
    assert part['offset']>=end,(name,'overlap')
    end=part['offset']+part['size']
assert end<=16*1024*1024,('flash overflow',end)
for name in ['ota_0','ota_1']:
    assert parts[name]['size']==6*1024*1024
    assert parts[name]['offset']%0x10000==0
firmware=(build/'xiaozhi.bin').stat().st_size
for name in ['ota_0','ota_1']:
    assert firmware<=parts[name]['size'],(name,'firmware overflow')
    print(f'{name}: {firmware} / {parts[name]["size"]} bytes; {parts[name]["size"]-firmware} bytes free')
flash=json.loads((build/'flasher_args.json').read_text())
for name,expected_hash in [
    ('assets','0a6e6a6c8ce73d91e9ceef3de3eb7450b35f40e4c42ab2850a1c15257214b711'),
    ('model','7183e030be52a41b0147d4c2ba05537c59d28c08992f5c2c623df0c75da5fe89')]:
    entry=flash[name]
    file=(build/entry['file']).resolve()
    assert int(entry['offset'],0)==parts[name]['offset'],(name,'flash offset mismatch')
    assert file.stat().st_size<=parts[name]['size'],(name,'payload overflow')
    assert hashlib.sha256(file.read_bytes()).hexdigest()==expected_hash,(name,'resource content changed')
    print(f'{name}: {file.stat().st_size} / {parts[name]["size"]} bytes, SHA256 unchanged, offset={entry["offset"]}')
assert int(flash['app']['offset'],0)==parts['ota_0']['offset']
assert flash['flash_settings']['flash_size']=='16MB'
print(f'Partition end: 0x{end:x}; overlap, 16 MiB limit and generated flash addresses passed.')
