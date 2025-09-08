// static/js/lib/http.js
const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';
export async function xfetch(url, opts={}) {
  const headers = new Headers(opts.headers || {});
  if (!headers.has('X-CSRFToken') && csrf()) headers.set('X-CSRFToken', csrf());
  return fetch(url, {...opts, headers});
}