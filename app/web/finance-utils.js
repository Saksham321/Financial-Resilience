/* Shared presentation policy; currency is explicit, never inferred from geography. */
'use strict';
const FinanceUI=Object.freeze({
 amount(value,code=null){if(value===null||value===undefined||!Number.isFinite(Number(value)))return 'Unavailable';const n=new Intl.NumberFormat('en-CA',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value));return n+(code?' '+code:' CAD');},
 number(value){return value===null||value===undefined||!Number.isFinite(Number(value))?'Unavailable':new Intl.NumberFormat('en-CA',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value));},
 percent(value){return value===null||value===undefined?'Unavailable':FinanceUI.number(value)+'%';},
 label(value){return String(({peak:'Savings',middle:'Wants',base:'Needs'})[String(value).toLowerCase()]??value??'Unavailable').replaceAll('_',' ').toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());},
 mask(value){return value===null||value===undefined?'Unavailable':'••••'+String(value).slice(-2);},
 threshold(actual,target){return actual===null||actual===undefined?'unknown':Number(actual)>Number(target)?'over':Number(target)-Number(actual)<=5?'near':'below';},
 stopAudio(except=null){if('speechSynthesis' in window)window.speechSynthesis.cancel();document.querySelectorAll('audio').forEach(a=>{if(a!==except)a.pause();});}
});

document.addEventListener('play',event=>{if(event.target.tagName==='AUDIO')FinanceUI.stopAudio(event.target);},true);
