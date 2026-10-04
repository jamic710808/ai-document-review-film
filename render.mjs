// Deterministic renderer: seek(t) -> screenshot -> ffmpeg. Usage:
//   node render.mjs --stills 0.5,10,20 --out stills     (contact stills)
//   node render.mjs --video out.mp4 [--audio master.wav]
import {createRequire} from 'node:module';
import {mkdirSync,readFileSync} from 'node:fs';
import {spawn} from 'node:child_process';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url);
const {chromium}=require('../promo-video/node_modules/playwright');
const a=process.argv.slice(2);const opt=(n,d)=>{const i=a.indexOf(n);return i<0?d:a[i+1]};
const TL=JSON.parse(readFileSync('timeline.json','utf8'));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
const errs=[];page.on('pageerror',e=>errs.push(e.message));page.on('requestfailed',r=>errs.push('REQ '+r.url()));
await page.goto(pathToFileURL(path.resolve('index.html')).href,{waitUntil:'load'});
await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})))});
if(opt('--stills')){
  const out=opt('--out','stills');mkdirSync(out,{recursive:true});
  for(const t of opt('--stills').split(',')){await page.evaluate(x=>window.seek(x),Number(t));await page.screenshot({path:`${out}/t${Number(t).toFixed(2).padStart(6,'0')}.png`})}
} else {
  const video=opt('--video','renders/film-silent.mp4');const audio=opt('--audio',null);mkdirSync(path.dirname(video),{recursive:true});
  const total=Math.round(TL.duration*TL.fps);
  const ff=['-y','-f','image2pipe','-framerate',String(TL.fps),'-i','-'];
  if(audio)ff.push('-i',audio,'-map','0:v','-map','1:a','-c:a','aac','-b:a','256k','-ar','48000');
  ff.push('-t',String(TL.duration),'-c:v','libx264','-crf','16','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',video);
  const p=spawn('ffmpeg',ff,{stdio:['pipe','ignore','pipe']});let se='';p.stderr.on('data',d=>se+=d);
  const done=new Promise((res,rej)=>p.on('close',c=>c===0?res():rej(new Error(se.slice(-800)))));
  for(let f=0;f<total;f++){
    await page.evaluate(t=>window.seek(t),f/TL.fps);
    const buf=await page.screenshot({type:'jpeg',quality:96});
    if(!p.stdin.write(buf))await new Promise(r=>p.stdin.once('drain',r));
    if(f%150===0)console.log(`frame ${f}/${total}`);
  }
  p.stdin.end();await done;console.log('OK',video);
}
if(errs.length)console.log('PAGE ERRORS:',errs);
await browser.close();
