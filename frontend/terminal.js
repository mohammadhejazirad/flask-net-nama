export class Terminal {
  constructor(element, onTruncate) {
    this.element = element; this.onTruncate = onTruncate; this.lines = []; this.pending = []; this.scheduled = false; this.bytes = 0;
    this.follow = true;
    element?.addEventListener('scroll', () => { this.follow = element.scrollHeight - element.scrollTop - element.clientHeight < 40; });
  }
  write(value) {
    if (!this.element) return;
    const text = String(value).replace(/\x1b\[[0-?]*[ -/]*[@-~]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '');
    this.pending.push(...text.slice(0, 65536).split('\n'));
    if (this.pending.length > 2000) {this.pending = this.pending.slice(-2000); this.onTruncate();}
    if (!this.scheduled) { this.scheduled = true; requestAnimationFrame(() => this.flush()); }
  }
  flush() {
    for (const line of this.pending) { this.lines.push(line); this.bytes += new TextEncoder().encode(line).length + 1; }
    this.pending = [];
    while (this.lines.length > 2000 || this.bytes > 1048576) { this.bytes -= new TextEncoder().encode(this.lines.shift()).length + 1; this.onTruncate(); }
    this.element.textContent = this.lines.join('\n');
    if (this.follow) this.element.scrollTop = this.element.scrollHeight;
    this.scheduled = false;
  }
  clear() {this.lines = []; this.pending = []; this.bytes = 0; this.element.textContent = '';}
}
