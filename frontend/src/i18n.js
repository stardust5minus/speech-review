import {useSyncExternalStore} from 'react';
import english from './locales/en.json';

const storageKey = 'speech-review-language';
let language = new URLSearchParams(location.search).get('lang');
if (!['en', 'zh'].includes(language)) {
  try { language = localStorage.getItem(storageKey); } catch {}
}
if (!['en', 'zh'].includes(language)) language = 'zh';
const listeners = new Set();
const reverse = Object.fromEntries(Object.entries(english).map(([zh, en]) => [en, zh]));
function makePatterns(dictionary) { return Object.entries(dictionary).filter(([key]) => /\{\d+\}/.test(key)).map(([zh,en]) => {
  const expression = zh.split(/\{\d+\}/).map(part => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('([\\s\\S]*?)');
  return [new RegExp('^' + expression + '$'), en];
}); }
const patterns = makePatterns(english);
const reversePatterns = makePatterns(reverse);
function format(text, args) {
  return text.replace(/\{(\d+)\}/g, (match, index) => args[index] ?? match);
}
function translate(value, args = []) {
  if (value == null) return value;
  const source = String(value);
  if (language === 'en') {
    if (english[source]) return format(english[source], args);
    for (const [pattern, target] of patterns) {
      const match = source.match(pattern);
      if (match) return format(target, match.slice(1));
    }
    return source;
  }
  if (reverse[source]) return format(reverse[source], args);
  for (const [pattern, target] of reversePatterns) {
    const match = source.match(pattern);
    if (match) return format(target, match.slice(1));
  }
  return format(source, args);
}
function applyLanguage() {
  document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
  document.title = language === 'en' ? 'Speech Review' : '复听工作台';
}
function setLanguage(next) {
  if (!['en', 'zh'].includes(next)) return;
  language = next;
  try { localStorage.setItem(storageKey, next); } catch {}
  const url = new URL(location.href);
  url.searchParams.set('lang', next);
  history.replaceState(null, '', url);
  applyLanguage();
  listeners.forEach(listener => listener());
}
window.addEventListener('storage', event => {
  if (event.key === storageKey && ['en', 'zh'].includes(event.newValue)) {
    language = event.newValue;
    applyLanguage();
    listeners.forEach(listener => listener());
  }
});
applyLanguage();
export function useLanguage() {
  const selected = useSyncExternalStore(listener => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }, () => language);
  return {tr: translate, language: selected, setLanguage};
}
