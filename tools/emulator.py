"""Minimal libretro test host. Runs the official Snes9x 1.63 core, not game logic.

This host drives real SNES controller input and captures PPU frames, SPC audio and
read-only WRAM telemetry. No gameplay state is modified by the test host.
"""
import ctypes as C
import math
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BUTTONS={'b':0,'y':1,'select':2,'start':3,'up':4,'down':5,'left':6,'right':7,'a':8,'x':9,'l':10,'r':11}
class GameInfo(C.Structure):
    _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]

class Emulator:
    def __init__(self,rom=None):
        self.core=C.CDLL(str(ROOT/'.tools/core/snes9x_libretro.dll'))
        self.held=[set(),set()];self.pixel_format=0;self.frame=None;self.frames=0
        self.audio_peak=0;self.audio_samples=0;self.audio_energy=0;self.pcm=bytearray()
        self.directory=str(ROOT/'.tools/core').encode()
        ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
        VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
        AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
        BATCH=C.CFUNCTYPE(C.c_size_t,C.POINTER(C.c_int16),C.c_size_t)
        POLL=C.CFUNCTYPE(None)
        INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
        def env(cmd,data):
            cmd &= 0xffff
            if cmd==10:self.pixel_format=C.cast(data,C.POINTER(C.c_uint))[0];return True
            if cmd==3:C.cast(data,C.POINTER(C.c_bool))[0]=True;return True
            if cmd in (9,31,30):C.cast(data,C.POINTER(C.c_char_p))[0]=self.directory;return True
            if cmd==15:return False
            if cmd==17:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
            if cmd==47:C.cast(data,C.POINTER(C.c_int))[0]=3;return True
            if cmd==39:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
            if cmd==52:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
            return cmd in (1,6,11,16,18,35,37,44,53,63)
        def video(data,width,height,pitch):
            if not data:return
            raw=C.string_at(data,pitch*height)
            if self.pixel_format==1:
                self.frame=Image.frombytes('RGB',(width,height),raw,'raw','BGRX',pitch)
            else:
                self.frame=Image.frombytes('RGB',(width,height),raw,'raw','BGR;16' if self.pixel_format==2 else 'BGR;15',pitch)
        def batch(data,frames):
            vals=C.cast(data,C.POINTER(C.c_int16*(frames*2))).contents
            for v in vals:
                self.audio_peak=max(self.audio_peak,abs(v));self.audio_energy+=v*v
            self.audio_samples+=frames*2
            if len(self.pcm)<32040*4*20:self.pcm.extend(C.string_at(data,frames*4))
            return frames
        def input_state(port,device,index,button):
            return int(port<2 and button in self.held[port])
        self.callbacks=[ENV(env),VIDEO(video),AUDIO(lambda l,r:None),BATCH(batch),POLL(lambda:None),INPUT(input_state)]
        for name,callback in zip(['environment','video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'],self.callbacks):
            getattr(self.core,'retro_set_'+name)(callback)
        self.core.retro_init()
        self.core.retro_load_game.argtypes=[C.POINTER(GameInfo)];self.core.retro_load_game.restype=C.c_bool
        self.core.retro_get_memory_data.argtypes=[C.c_uint];self.core.retro_get_memory_data.restype=C.c_void_p
        self.core.retro_get_memory_size.argtypes=[C.c_uint];self.core.retro_get_memory_size.restype=C.c_size_t
        self.rompath=Path(rom or ROOT/'dist/abaqus-after-hours.sfc')
        self.rom=C.create_string_buffer(self.rompath.read_bytes())
        info=GameInfo(str(self.rompath).encode(),C.cast(self.rom,C.c_void_p),len(self.rom)-1,None)
        if not self.core.retro_load_game(C.byref(info)):raise RuntimeError('Snes9x rejected the ROM')
        self.core.retro_set_controller_port_device(0,1);self.core.retro_set_controller_port_device(1,1)
        self.ram=self.core.retro_get_memory_data(2)
        assert self.core.retro_get_memory_size(2)==131072
    def run(self,n=1,p1=(),p2=()):
        self.held=[{BUTTONS[x] for x in p1},{BUTTONS[x] for x in p2}]
        for _ in range(n):self.core.retro_run();self.frames+=1
        return self.state()
    def tap(self,key,port=0):
        self.run(3,**({'p1':[key]} if port==0 else {'p2':[key]}));return self.run(3)
    def state(self):
        # The first 32 words are the original public trace.  The roster
        # upgrade appends ten read-only words for per-character identity,
        # special family, movement profile and facing.  Reading the larger
        # window is harmless with an older ROM and keeps callers compatible.
        data=C.string_at(self.ram+0x1ff00,188)
        vals=[int.from_bytes(data[i:i+2],'little') for i in range(0,64,2)]
        names=['magic','screen','frame','mode','hp1','hp2','x1','x2','y1','y2','action1','action2','wins1','wins2','arena','round','intro','paused','energy1','energy2','wave1','wave2','selected','selected2','arcade','seconds','pose1','pose2','round_end','hitstop','combo','champion']
        result=dict(zip(names,vals))
        extension=['fighter_id1','fighter_id2','family1','family2','speed1','speed2','jump1','jump2','face1','face2',
                   'back_speed1','back_speed2','special_startup1','special_startup2',
                   'special_active1','special_active2','special_recovery1','special_recovery2',
                   'special_damage1','special_damage2','special_reach1','special_reach2',
                   'throw_range1','throw_range2','wave_low1','wave_low2',
                   'wave_speed1','wave_speed2','wave_life1','wave_life2']
        result.update(dict(zip(extension,[int.from_bytes(data[i:i+2],'little') for i in range(64,124,2)])))
        animation=['anim_frame1','anim_frame2','anim_state1','anim_state2',
                   'anim_tick1','anim_tick2','buffered_action1','buffered_action2',
                   'buffer_age1','buffer_age2','jump_buffer1','jump_buffer2',
                   'command_stage1','command_stage2','raw_keys1','raw_keys2','landing1','landing2',
                   'jump_vx1','jump_vx2']
        result.update(dict(zip(animation,[int.from_bytes(data[i:i+2],'little') for i in range(124,164,2)])))
        contact=['hurt1','hurt2','guard1','guard2','connected1','connected2',
                 'combo1','combo2','combo_display1','combo_display2','counter1','counter2']
        result.update(dict(zip(contact,[int.from_bytes(data[i:i+2],'little') for i in range(164,188,2)])))
        return result
    def shot(self,name):
        path=ROOT/'docs/screenshots'/name;path.parent.mkdir(exist_ok=True,parents=True)
        assert self.frame is not None
        self.frame.save(path)
        return path
    def close(self):
        self.core.retro_unload_game();self.core.retro_deinit()

if __name__=='__main__':
    e=Emulator();print(e.run(180));print(e.shot('title.png'))
    e.tap('start');print(e.run(10));print(e.shot('select.png'))
    e.tap('a');print(e.run(10));print(e.shot('arenas.png'))
    e.tap('a');print(e.run(140));print(e.shot('fight.png'))
    print('Audio peak:',e.audio_peak,'samples:',e.audio_samples)
    e.close()
