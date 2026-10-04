import json,re,subprocess,wave,sys
sys.stdout.reconfigure(encoding='utf-8')
items=json.load(open('narration.json',encoding='utf-8'))
def dur(k):
    w=wave.open(f'audio/{k}.wav');return w.getnframes()/w.getframerate()
def chunks(k,d):
    out=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',f'audio/{k}.wav','-af','silencedetect=noise=-38dB:d=0.12','-f','null','-'],capture_output=True,text=True).stderr
    st=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',out)]
    en=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',out)]
    # speech spans = between silence_end[i] and silence_start[i+1]
    spans=[];cur=0.0
    for s,e in zip(st,en):
        if s-cur>0.08: spans.append([cur,s])
        cur=e
    if d-cur>0.08: spans.append([cur,d])
    return spans
LEAD=0.3; TAIL=0.5
t=0.0; beats=[]
for i,(k,text) in enumerate(items):
    d=dur(k); lead=0.2 if i==0 else LEAD
    tail=TAIL+(2.4 if k=='b11' else 0)
    sp=chunks(k,d)
    beats.append(dict(id=k,text=text,start=round(t,3),voiceStart=round(t+lead,3),voiceDur=round(d,3),end=round(t+lead+d+tail,3),speech=[[round(a,3),round(b,3)] for a,b in sp]))
    t=beats[-1]['end']
TL=dict(fps=30,width=1920,height=1080,duration=round(t,3),beats=beats)
open('timeline.json','w',encoding='utf-8').write(json.dumps(TL,ensure_ascii=False,indent=1))
open('timeline.js','w',encoding='utf-8').write('window.TL='+json.dumps(TL,ensure_ascii=False)+';')
for b in beats: print(b['id'],b['start'],b['end'],b['speech'])
print('total',TL['duration'])
