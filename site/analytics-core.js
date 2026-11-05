/* Pure analytics utilities. No network access, no inference of incident locations. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.NACINAnalytics = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function() {
  'use strict';
  const STATES = ['Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal','Andaman and Nicobar Islands','Chandigarh','Dadra and Nagar Haveli and Daman and Diu','Delhi','Jammu and Kashmir','Ladakh','Lakshadweep','Puducherry'];
  const STATE_ALIASES = {'nct of delhi':'Delhi','new delhi':'Delhi','orissa':'Odisha','pondicherry':'Puducherry','uttaranchal':'Uttarakhand','jammu & kashmir':'Jammu and Kashmir','andaman & nicobar islands':'Andaman and Nicobar Islands','dadra and nagar haveli':'Dadra and Nagar Haveli and Daman and Diu','daman and diu':'Dadra and Nagar Haveli and Daman and Diu'};
  const COUNTRY_ALIASES = {'usa':'United States','us':'United States','u.s.':'United States','united states of america':'United States','uk':'United Kingdom','u.k.':'United Kingdom','uae':'United Arab Emirates','viet nam':'Vietnam','russian federation':'Russia','bharat':'India','republic of india':'India','dr congo':'Democratic Republic of the Congo'};
  const COUNTRY_NAMES = ['India','China','Thailand','Vietnam','Indonesia','Malaysia','Singapore','Bangladesh','Nepal','Sri Lanka','Myanmar','Laos','Cambodia','Philippines','Japan','South Korea','Pakistan','Afghanistan','Mongolia','Russia','United Arab Emirates','Saudi Arabia','Qatar','Oman','Iran','Turkey','Israel','Kenya','Tanzania','Uganda','South Africa','Zimbabwe','Zambia','Mozambique','Namibia','Botswana','Malawi','Nigeria','Ghana','Cameroon','Democratic Republic of the Congo','Republic of the Congo','Central African Republic','Ethiopia','Madagascar','Egypt','Morocco','Sudan','United States','Canada','Mexico','Brazil','Peru','Colombia','Ecuador','Bolivia','Argentina','Chile','Costa Rica','Panama','Guatemala','Cuba','United Kingdom','France','Germany','Spain','Italy','Netherlands','Belgium','Portugal','Switzerland','Poland','Greece','Sweden','Norway','Finland','Ukraine','Australia','New Zealand','Papua New Guinea','Fiji'];
  const knownCountries = new Map(COUNTRY_NAMES.map(n => [n.toLowerCase(),n]));
  function country(v) {
    if (typeof v !== 'string') return null;
    const s=v.trim().toLowerCase();
    if (!s || ['unknown','not specified','n/a','other'].includes(s)) return null;
    const name=COUNTRY_ALIASES[s]||knownCountries.get(s);
    return name || null;
  }
  function state(v) {
    if (typeof v !== 'string') return null;
    const s=v.trim().toLowerCase();
    return STATE_ALIASES[s]||STATES.find(n=>n.toLowerCase()===s)||null;
  }
  function date(v) {
    if(typeof v!=='string' || !/^\d{4}-\d{2}-\d{2}(?:T|$)/.test(v)) return null;
    const d=new Date(v.length===10?v+'T00:00:00Z':v);
    return Number.isNaN(d.getTime())?null:d;
  }
  function species(v) {
    const parts=Array.isArray(v)?v:typeof v==='string'?v.split(','):[];
    return [...new Set(parts.map(s=>String(s).trim()).filter(s=>s && !['unknown','not specified','none','n/a'].includes(s.toLowerCase())))];
  }
  const verified=a=>a&&a.metadata_status==='verified';
  function filter(records,period='all') {
    const arr=Array.isArray(records)?records.filter(a=>a&&a.status==='published'):[];
    if(period==='all') return arr;
    const days=Number(period);if(![30,90,365].includes(days)) return arr;
    return arr.filter(a=>{const d=date(a.published_at);return d && d.getTime()>=Date.now()-days*86400000;});
  }
  function add(map,key,a){if(!map[key])map[key]=[];map[key].push(a);}
  function analyze(records) {
    const global={},india={},bySpecies={},byMonth={};let verifiedReports=0,verifiedSpecies=0,unknownCountry=0,indianUnknownState=0,unknownDates=0;
    for (const a of records) {
      if(verified(a)) {
        verifiedReports++;
        const c=country(a.incident_country);
        if(c) {add(global,c,a);if(c==='India'){const s=state(a.incident_state);if(s)add(india,s,a);else indianUnknownState++;}}
        else unknownCountry++;
        const names=species(a.species);
        if(names.length) verifiedSpecies++;
        for(const n of names) add(bySpecies,n,a);
      } else unknownCountry++;
      const d=date(a.published_at);
      if(d) add(byMonth,d.toISOString().slice(0,7),a);else unknownDates++;
    }
    return {global,india,bySpecies,byMonth,verifiedReports,verifiedSpecies,unknownCountry,indianUnknownState,unknownDates};
  }
  return {STATES,country,state,date,species,filter,analyze,verified};
});
