import{_ as O}from"./preload-helper.CLcXU_4U.js";import{c as y,l as g,F as h}from"./index.CS6OrWfV.js";import{g as C}from"./spectrum.CR16cYRR.js";import"./index.CgyfDPEE.js";const q=`<CsoundSynthesizer>\r
<CsInstruments>\r
\r
sr=48000\r
ksmps=64\r
nchnls=2\r
0dbfs=1\r
\r
</CsInstruments>\r
</CsoundSynthesizer>`,$=`; returns value of given key in given "string map"\r
; keymap("freq", "note/c3/freq/220/gain/0.5")\r
; yields "220"\r
opcode keymap, S, SS\r
  Skey, Smap xin\r
  idelimiter = strindex(Smap, strcat(Skey, "/"))\r
  ifrom = idelimiter + strlen(Skey) + 1\r
  Svalue = strsub(Smap, ifrom, strlen(Smap))\r
  Svalue = strsub(Svalue, 0, strindex(Svalue, "/"))\r
  xout Svalue\r
endop\r
\r
; TODO add incredibly dope synths\r
instr organ\r
    iduration = p3\r
    ifreq = p4\r
    igain = p5\r
    ioct = octcps(ifreq)\r
\r
    asig = vco2(igain, ifreq, 12, .5) ; my edit\r
    kpwm = oscili(.1, 5)\r
    asig = vco2(igain, ifreq, 4, .5 + kpwm)\r
    asig += vco2(igain/4, ifreq * 2)\r
\r
    ; filter\r
    ; idepth = 2\r
    ; acut = transegr:a(0, .005, 0, idepth, .06, -4.2, 0.001, .01, -4.2, 0) ; filter envelope\r
    ; asig = zdf_2pole(asig, cpsoct(ioct + acut), 0.5)\r
\r
    ; amp envelope\r
    iattack = .001\r
    irelease = .05\r
    asig *= linsegr:a(0, iattack, 1, iduration, 1, irelease, 0)\r
\r
    out(asig, asig)\r
\r
endin\r
\r
instr triangle\r
  iduration = p3\r
  ifreq = p4\r
  igain = p5\r
  ioct = octcps(ifreq)\r
  \r
  asig = vco2(igain, ifreq, 12, .5)\r
  \r
  ; amp envelope\r
  iattack = .001\r
  irelease = .05\r
  asig *= linsegr:a(0, iattack, 1, iduration, 1, irelease, 0)\r
  \r
  out(asig, asig)\r
endin\r
\r
instr pad\r
    iduration = p3\r
    ifreq = p4\r
    igain = p5\r
    ioct = octcps(ifreq)\r
\r
    asig = vco2(igain, ifreq, 0)\r
\r
    ; amp envelope\r
    iattack = .5\r
    irelease = .1\r
    asig *= linsegr:a(0, iattack, 1, iduration, 1, irelease, 0)\r
    \r
    idepth = 2\r
    acut = transegr:a(0, .005, 0, idepth, .06, -4.2, 0.001, .01, -4.2, 0)\r
    asig = zdf_2pole(asig, 1000, 2)\r
\r
    out(asig, asig)\r
endin\r
\r
\r
gisine	ftgen	0, 0, 4096, 10, 1\r
\r
instr bow\r
    kpres = 2\r
    krat = 0.16\r
    kvibf = 6.12723\r
    \r
    kvib  linseg 0, 0.5, 0, 1, 1, p3-0.5, 1	\r
    kvamp = kvib * 0.01\r
    asig  wgbow .7, p4, kpres, krat, kvibf, kvamp, gisine\r
    asig = asig*p5\r
    outs asig, asig\r
endin\r
\r
\r
instr Meta\r
    Smap = strget(p6)\r
    Sinstrument = keymap("s", Smap)\r
    schedule(Sinstrument, 0, p3, p4, p5)\r
    ; TODO find a way to pipe Sinstrument through effects\r
endin`;let u,t;async function k(n=""){await d(),n&&(n=`${n}`,await t?.evalCode(n))}const D=k,I=k,L=y("csound",(n,e)=>(n=n||"triangle",d(),e.onTrigger((r,i,f,m)=>{if(!t){g("[csound] not loaded yet","warning");return}r.ensureObjectValue();let{gain:a=.8}=r.value;a*=.2;const o=Math.round(h(r)),p=Object.entries({...r.value,freq:o}).flat().join("/"),c=m-i,s=`i ${[`"${n}"`,c,r.duration+0,o,a,`"${p}"`].join(" ")}`;t.inputMessage(s)})));function x(n,e){const[r]=e;if(n==="message"&&(["[commit: HEAD]"].includes(r)||r.startsWith("--Csound version")||r.startsWith("libsndfile")||r.startsWith("sr =")||r.startsWith("0dBFS")||r.startsWith("audio buffered")||r.startsWith("writing")||r.startsWith("SECTION 1:")))return;let i="info";r.startsWith("error:")&&(i="error"),g(`[csound] ${r||""}`,i)}async function W(){if(window.__csound__)return g("[load] Using external Csound","warning"),t=window.__csound__,t;{const{Csound:n}=await O(async()=>{const{Csound:e}=await import("./csound.-DfvzaX-.js");return{Csound:e}},[]);return t=await n({audioContext:C()}),t.removeAllListeners("message"),["message"].forEach(e=>t.on(e,(...r)=>x(e,r))),await t.setOption("-m0d"),await t.setOption("--sample-accurate"),await t.setOption("-odac"),await t.compileCsdText(q),await t.compileOrc($),await t.start(),t}}async function d(){return u=u||W(),u}let l={};async function F(n){if(await d(),typeof n!="string")throw new Error("loadOrc: expected url string");if(n.startsWith("github:")){const[e,r]=n.split("github:");n=`https://raw.githubusercontent.com/${r}`}l[n]||(l[n]=fetch(n).then(e=>e.text()).then(e=>t.compileOrc(e))),await l[n]}const P=y("csoundm",(n,e)=>{let r=n;return typeof n=="string"&&(r=`"${n}"`),d(),e.onTrigger((i,f,m,a)=>{if(!t){g("[csound] not loaded yet","warning");return}if(typeof i.value!="object")throw new Error("csound only support objects as hap values");const o=a-f,p=i.duration.valueOf()+0,c=h(i);let{gain:v=1,velocity:s=.9}=i.value;s=v*s;const S=(Math.log(c/261.62558)/Math.log(2)+8)*12-36,_=127*s,b=Object.entries({...i.value,frequency:c}).flat().join("/"),w=`i ${r} ${o} ${p} ${S} ${_} "${b}"`;console.log("[csoundm]:",w),t.inputMessage(w)})});export{L as csound,P as csoundm,k as loadCSound,I as loadCsound,F as loadOrc,D as loadcsound};
