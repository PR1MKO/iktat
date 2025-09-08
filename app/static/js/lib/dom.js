// static/js/lib/dom.js
export const $  = (sel, ctx=document) => ctx.querySelector(sel);
export const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));
export const on = (el, evt, handler, opts) => el && el.addEventListener(evt, handler, opts);
export const delegate = (root, evt, selector, handler) =>
  on(root, evt, e => e.target.closest(selector) && handler(e));