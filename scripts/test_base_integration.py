"""Run the actual firmware UART parsing loop as a host DLL against stream cases."""
from pathlib import Path
import ctypes
import subprocess
import tempfile
import sys

body=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
root=body.parent/'esp-echoear-base/software/echoear_rotating_base'
source=(root/'components/control_serial/control_serial.c').read_text(encoding='utf-8')
doa_source=(body/'components/audio_doa/audio_doa_tracker.c').read_text(encoding='utf-8')
qa=doa_source.index('static float quantize_angle(float angle)')
qb=doa_source.index('\n/**',qa)
quantize=doa_source[qa:qb]
a=source.index('        used += len;')
b=source.index('        used -= offset;',a)+len('        used -= offset;')
loop=source[a:b]
vswhere=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe')
compiler=Path(subprocess.check_output([str(vswhere),'-latest','-products','*','-find',r'VC\Tools\MSVC\**\bin\Hostx64\x64\cl.exe'],text=True).strip())
link=compiler.with_name('link.exe')
prefix='''typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned long long size_t;
typedef struct { uint8_t cmd; uint16_t value; } base_command_t;
#define UART_FRAME_HEAD_H 0xAA
#define UART_FRAME_HEAD_L 0x55
#define CMD_BASE_ANGLE_CONTROL 1
#define CMD_BASE_ACTION_CONTROL 2
#define CMD_MAGNETIC_SWITCH_EVENT 3
#define pdTRUE 1
#define ESP_LOGW(...) ((void)0)
static uint8_t buffer[1024];
static size_t used;
static int s_angles, s_commands, n;
static base_command_t results[128];
static int xQueueOverwrite(int q, base_command_t *c) { results[n++]=*c; return 1; }
static int xQueueSend(int q, base_command_t *c, int t) { results[n++]=*c; return 1; }
static void memmove(uint8_t *dst, const uint8_t *src, size_t len) {
    for(size_t i=0;i<len;++i) dst[i]=src[i];
}
__declspec(dllexport) void reset(void) { used=0; n=0; }
__declspec(dllexport) int count(void) { return n; }
__declspec(dllexport) int value(int i) { return results[i].value; }
__declspec(dllexport) int command(int i) { return results[i].cmd; }
__declspec(dllexport) void feed(const uint8_t *input, int len) {
    for(int i=0;i<len;++i) buffer[used+i]=input[i];
'''
numeric='''
int _fltused = 0;
#define ANGLE_QUANTIZATION_STEP 5.0f
#define ANGLE_MIN 0.0f
#define ANGLE_MAX 180.0f
/* Isolate firmware logic from the host CRT; these implement standard math helpers. */
static float roundf(float x) { return (float)(int)(x >= 0 ? x+0.5f : x-0.5f); }
static float fminf(float a, float b) { return a < b ? a : b; }
static float fmaxf(float a, float b) { return a > b ? a : b; }
'''+quantize+'''
__declspec(dllexport) float quantize_result(float angle) { return quantize_angle(angle); }
'''
def frame(cmd,value):
    high,low=divmod(value,256)
    return bytes([0xAA,0x55,0,3,cmd,high,low,(cmd+high+low)&255])
with tempfile.TemporaryDirectory(prefix='echoear-parser-') as tmp:
    tmp=Path(tmp); c=tmp/'parser.c'; obj=tmp/'parser.obj'; dll=tmp/'parser.dll'
    c.write_text(prefix+loop+'\n}\n'+numeric,encoding='utf-8')
    subprocess.run([str(compiler),'/nologo','/GS-','/Oi-','/c',str(c),f'/Fo{obj}'],check=True)
    subprocess.run([str(link),'/nologo','/dll','/noentry','/nodefaultlib',f'/out:{dll}',str(obj)],check=True)
    lib=ctypes.CDLL(str(dll)); lib.feed.argtypes=[ctypes.c_char_p,ctypes.c_int]
    tests=0
    def check(chunks,expected):
        global tests
        lib.reset()
        for chunk in chunks: lib.feed(chunk,len(chunk))
        actual=[(lib.command(i),lib.value(i)) for i in range(lib.count())]
        assert actual==expected,(chunks,actual,expected)
        tests+=1
    f=frame(1,120)
    for split in range(1,8): check([f[:split],f[split:]],[(1,120)])
    check([bytes([b]) for b in f],[(1,120)])
    check([f+frame(2,4)+frame(3,16)],[(1,120),(2,4),(3,16)])
    check([b'noise\xaa',f],[(1,120)])
    check([f[:-1]+bytes([f[-1]^1])+frame(2,0)],[(2,0)])
    check([b'\xaa\x55\xff\xff'+f],[(1,120)])
    check([f[:6]],[])
    check([frame(1,181)+frame(2,1)],[(2,1)])
    check([f*100],[(1,120)]*100)
    print(f'{tests} actual C UART parser regression cases passed.')
    lib.quantize_result.argtypes=[ctypes.c_float]
    lib.quantize_result.restype=ctypes.c_float
    for i in range(721):
        angle=i/4
        result=lib.quantize_result(angle)
        assert 0 <= result <= 180 and result % 5 == 0 and abs(result-angle) <= 2.5,(angle,result)
    assert lib.quantize_result(90)==90
    print('721 actual C DOA quantization cases passed; 90-degree center preserved.')
    ctypes.windll.kernel32.FreeLibrary(ctypes.c_void_p(lib._handle))
