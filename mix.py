"""Mix Kore narration + extended reference music + soft SFX. Levels follow the skill: narration on top,
music ducked under speech, each effect solved to lift ~3.5 dB in its own band over the music bed (2-8 kHz capped at 4 dB)."""
import json,subprocess,sys,numpy as np,wave
def _band(x,lo,hi,fs):
    X=np.fft.rfft(x);f=np.fft.rfftfreq(len(x),1/fs);m=np.ones_like(f)
    if lo:m*=1/(1+(lo/np.maximum(f,1e-3))**4)       # 2nd-order-ish high-pass (smooth)
    if hi:m*=1/(1+(f/hi)**4)
    return np.fft.irfft(X*m,len(x)).astype(np.float32)
sys.stdout.reconfigure(encoding='utf-8')
SR=48000
TL=json.load(open('timeline.json',encoding='utf-8'));DUR=TL['duration'];N=int(DUR*SR)
def load(p,ch=2):
    r=subprocess.run(['ffmpeg','-v','error','-i',p,'-ac',str(ch),'-ar',str(SR),'-f','f32le','-'],capture_output=True)
    a=np.frombuffer(r.stdout,np.float32).copy();return a.reshape(-1,ch) if ch>1 else a
def place(buf,x,t):
    i=int(t*SR);n=min(len(x),len(buf)-i)
    if n>0:buf[i:i+n]+=x[:n]
# --- voice (mono -> centre)
voice=np.zeros(N,np.float32)
for b in TL['beats']:
    v=load(f"audio/{b['id']}.wav",1);v=v/ (np.abs(v).max()+1e-9)*0.85
    f=int(.008*SR);v[:f]*=np.linspace(0,1,f);v[-f:]*=np.linspace(1,0,f)
    place(voice,v,b['voiceStart'])
voice=_band(voice,80,None,SR)
# --- music, ducked under speech
music=load('assets/music/music_ext.wav',2)[:N]
if len(music)<N:music=np.pad(music,((0,N-len(music)),(0,0)))
env=np.sqrt(np.convolve(voice**2,np.ones(int(.05*SR))/int(.05*SR),'same'))
act=(env>0.02).astype(np.float32)
a=np.exp(-1/(0.06*SR));r=np.exp(-1/(0.45*SR));g=np.zeros(N,np.float32);cur=0.0
for i in range(0,N):  # smooth attack/release
    tgt=act[i];cur=(a*cur+(1-a)*tgt) if tgt>cur else (r*cur+(1-r)*tgt);g[i]=cur
duck_db=-9.0
mg=10**((duck_db*g)/20)
rms=lambda x:np.sqrt((x**2).mean()+1e-12)
music=music*mg[:,None]
vr=rms(voice[voice!=0]);mr=rms(music)
music*=vr*10**(-17/20)/mr      # music ~17 dB under voice RMS on average
# --- sfx
plan=[]
def cue(beat,lt,f,gain=1.0):plan.append((beat,lt,f,gain))
for b in TL['beats'][1:]:cue(b['id'],-0.1,'whoosh',0.8)
cue('b03',.85,'sweep',.8);[cue('b03',t,'toggle',.7) for t in (1.9,2.9,4.1)]
cue('b04',.3,'pop');[cue('b04',t,'toggle',.5) for t in (1.7,3.0,4.3)]
cue('b05',.45,'pop');cue('b05',4.7,'click');cue('b05',6.4,'ding-dong',.8)
cue('b06',.9,'click');cue('b06',2.45,'pop')
[cue('b07',t,'toggle',.7) for t in (3.45,4.1,4.85)];cue('b07',6.9,'click');cue('b07',7.05,'success',.8)
cue('b08',2.4,'pop');cue('b08',5.0,'click');
cue('b09',.8,'pop',.8);cue('b09',1.9,'pop');cue('b09',3.6,'click');cue('b09',5.3,'click');cue('b09',5.5,'resolve',.8)
[cue('b10',t,'toggle',.6) for t in (.7,1.15,1.6)];cue('b10',3.9,'pop');cue('b10',4.2,'pop')
cue('b11',.6,'resolve',.9)
start={b['id']:b['start'] for b in TL['beats']}
W=int(.3*SR)
def pk(y):
    h=int(.05*SR);return max(10*np.log10((y[i:i+h]**2).mean()+1e-12) for i in range(0,max(1,len(y)-h),h//2))
mono=music.mean(1)
sfx=np.zeros((N,2),np.float32);report=[]
SOLVED={}
cache={}
for beat,lt,name,rel in plan:
    t=start[beat]+lt
    if name not in cache:
        s=load(f'assets/sfx/{name}.wav',1)
        s=_band(s,180,9500,SR)
        f=int(.004*SR);s[:f]*=np.linspace(0,1,f);s[-f:]*=np.linspace(1,0,f);s=s/(np.abs(s).max()+1e-9);cache[name]=s.astype(np.float32)
    s=cache[name];i=int(t*SR);pad=SR//2
    base=mono[max(0,i-pad):i+len(s)+pad];base=np.pad(base,(0,max(0,len(s)+2*pad-len(base))))
    F=np.abs(np.fft.rfft(s*np.hanning(len(s))))**2;fq=np.fft.rfftfreq(len(s),1/SR);c=np.cumsum(F)/F.sum()
    lo=max(fq[np.searchsorted(c,.2)],200);hi=min(max(fq[np.searchsorted(c,.8)],lo*2),SR/2-500)
    Wd=int(.3*SR);BP=lambda y:_band(_band(y,lo,None,SR),None,hi,SR);HBf=lambda y:_band(_band(y,2000,None,SR),None,8000,SR);b0=max(pk(BP(base)[pad:pad+Wd]),-52);h0=max(pk(HBf(base)[pad:pad+Wd]),-50);gg=prev=.002
    for x in np.geomspace(.002,1.0,60):
        seg=base.copy();seg[pad:pad+len(s)]+=x*s
        if pk(HBf(seg)[pad:pad+Wd])-h0>4.5:gg=prev;break
        if pk(BP(seg)[pad:pad+Wd])-b0>=4.5:gg=x;break
        prev=x
    gg=float(np.clip(gg,.01,.35))*rel
    SOLVED.setdefault(name,[]).append((t,gg,rel))
for name,lst in SOLVED.items():
    med=float(np.median([g/r for _,g,r in lst]))
    for t,g,r in lst:
        gg=float(np.clip(g/r,.7*med,1.3*med))*r*1.5   # same sound -> same level (+3.5 dB overall presence)
        place(sfx[:,0],cache[name]*gg,t);place(sfx[:,1],cache[name]*gg,t);report.append((name,round(t,2),round(gg,3)))
json.dump(report,open('review/sfx-gains.json','w'),ensure_ascii=False)
mix=music+sfx+voice[:,None]
def save(p,x):
    x=np.clip(x,-1,1);w=wave.open(p,'wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((x*32767).astype('<i2').tobytes());w.close()
save('audio/_premaster.wav',mix);save('audio/_music_only.wav',music+voice[:,None]*0)
save('audio/_voice_music.wav',music+voice[:,None])
print('rms voice',20*np.log10(vr),'music',20*np.log10(rms(music)))
