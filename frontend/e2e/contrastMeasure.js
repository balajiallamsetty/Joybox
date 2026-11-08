import zlib from 'node:zlib';

function channel(c) {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(rgb) {
  return 0.2126 * channel(rgb.r) + 0.7152 * channel(rgb.g) + 0.0722 * channel(rgb.b);
}

export function contrastRatio(fg, bg) {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

export function hex(rgb) {
  const h = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0');
  return `#${h(rgb.r)}${h(rgb.g)}${h(rgb.b)}`;
}

export function decodePng(buffer) {
  const buf = Buffer.from(buffer);
  let offset = 8;
  let width = 0;
  let height = 0;
  let colorType = 6;
  const idat = [];
  while (offset + 8 <= buf.length) {
    const len = buf.readUInt32BE(offset);
    offset += 4;
    const type = buf.toString('ascii', offset, offset + 4);
    offset += 4;
    const data = buf.subarray(offset, offset + len);
    offset += len + 4;
    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      colorType = data[9];
    } else if (type === 'IDAT') {
      idat.push(data);
    } else if (type === 'IEND') {
      break;
    }
  }
  const inflated = zlib.inflateSync(Buffer.concat(idat));
  const bpp = colorType === 6 ? 4 : colorType === 2 ? 3 : colorType === 4 ? 2 : 1;
  const stride = width * bpp;
  const pixels = new Uint8ClampedArray(width * height * 4);
  let src = 0;
  const prev = Buffer.alloc(stride);
  const row = Buffer.alloc(stride);
  for (let y = 0; y < height; y += 1) {
    const filter = inflated[src];
    src += 1;
    inflated.copy(row, 0, src, src + stride);
    src += stride;
    for (let i = 0; i < stride; i += 1) {
      const left = i >= bpp ? row[i - bpp] : 0;
      const up = prev[i];
      const ul = i >= bpp ? prev[i - bpp] : 0;
      let value = row[i];
      if (filter === 1) value = (value + left) & 255;
      else if (filter === 2) value = (value + up) & 255;
      else if (filter === 3) value = (value + Math.floor((left + up) / 2)) & 255;
      else if (filter === 4) {
        const p = left + up - ul;
        const pa = Math.abs(p - left);
        const pb = Math.abs(p - up);
        const pc = Math.abs(p - ul);
        const pred = pa <= pb && pa <= pc ? left : pb <= pc ? up : ul;
        value = (value + pred) & 255;
      }
      row[i] = value;
    }
    row.copy(prev);
    for (let x = 0; x < width; x += 1) {
      const di = (y * width + x) * 4;
      if (bpp === 4) {
        pixels[di] = row[x * 4];
        pixels[di + 1] = row[x * 4 + 1];
        pixels[di + 2] = row[x * 4 + 2];
        pixels[di + 3] = row[x * 4 + 3];
      } else if (bpp === 3) {
        pixels[di] = row[x * 3];
        pixels[di + 1] = row[x * 3 + 1];
        pixels[di + 2] = row[x * 3 + 2];
        pixels[di + 3] = 255;
      } else if (bpp === 2) {
        pixels[di] = row[x * 2];
        pixels[di + 1] = row[x * 2];
        pixels[di + 2] = row[x * 2];
        pixels[di + 3] = row[x * 2 + 1];
      } else {
        pixels[di] = row[x];
        pixels[di + 1] = row[x];
        pixels[di + 2] = row[x];
        pixels[di + 3] = 255;
      }
    }
  }
  return { width, height, pixels };
}

function worstBackground(png, fg) {
  const { width, height, pixels } = png;
  let worst = null;
  let worstRatio = Infinity;
  const step = Math.max(1, Math.floor(Math.sqrt((width * height) / 4000)));
  for (let y = 0; y < height; y += step) {
    for (let x = 0; x < width; x += step) {
      const i = (y * width + x) * 4;
      if (pixels[i + 3] < 16) continue;
      const bg = { r: pixels[i], g: pixels[i + 1], b: pixels[i + 2] };
      const ratio = contrastRatio(fg, bg);
      if (ratio < worstRatio) {
        worstRatio = ratio;
        worst = bg;
      }
    }
  }
  return worst ? { bg: worst, ratio: worstRatio } : null;
}

const COLLECT = () => {
  const parse = (value) => {
    if (!value) return null;
    const match = String(value).match(/rgba?\(([^)]+)\)/);
    if (!match) return null;
    const parts = match[1].split(',').map((part) => Number.parseFloat(part.trim()));
    if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) return null;
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };

  const blend = (fg, bg) => {
    const a = fg.a === undefined ? 1 : fg.a;
    return {
      r: fg.r * a + bg.r * (1 - a),
      g: fg.g * a + bg.g * (1 - a),
      b: fg.b * a + bg.b * (1 - a),
    };
  };

  const opaqueBackground = (el) => {
    let node = el;
    let opacity = 1;
    while (node && node !== document.documentElement.parentElement) {
      const style = getComputedStyle(node);
      const own = Number.parseFloat(style.opacity || '1');
      if (!Number.isNaN(own)) opacity *= own;
      const image = style.backgroundImage;
      const bg = parse(style.backgroundColor);
      if (bg && bg.a >= 0.99) return { complex: false, covered: true, color: bg, opacity };
      if (image && image !== 'none') return { complex: true };
      if (style.backdropFilter && style.backdropFilter !== 'none') return { complex: true };
      node = node.parentElement;
    }
    return { complex: false, covered: false, color: { r: 255, g: 255, b: 255, a: 1 }, opacity };
  };

  const overlapsImage = (rect) => {
    const images = document.querySelectorAll('img, video, canvas');
    for (const image of images) {
      const box = image.getBoundingClientRect();
      const hits = rect.left < box.right && rect.right > box.left && rect.top < box.bottom && rect.bottom > box.top;
      if (!hits) continue;
      const style = getComputedStyle(image);
      if (style.display === 'none' || style.visibility === 'hidden' || Number.parseFloat(style.opacity) === 0) continue;
      return true;
    }
    return false;
  };

  const pathFor = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 5) {
      let part = node.tagName.toLowerCase();
      if (node.id) {
        parts.unshift(`#${CSS.escape(node.id)}`);
        break;
      }
      const classes = [...node.classList].filter((name) => !name.startsWith('hover:') && name.length < 40).slice(0, 2);
      if (classes.length) part += `.${classes.map((name) => CSS.escape(name)).join('.')}`;
      const parent = node.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter((child) => child.tagName === node.tagName);
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  };

  const visible = (el) => {
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    if (Number.parseFloat(style.opacity || '1') === 0) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 1 && rect.height >= 1;
  };

  const records = [];
  const seen = new Set();
  const push = (record) => {
    const key = [
      record.kind,
      record.text.slice(0, 40),
      record.className.slice(0, 80),
      Math.round(record.fg.r),
      Math.round(record.fg.g),
      Math.round(record.fg.b),
      record.bg ? Math.round(record.bg.r) : 'c',
      record.bg ? Math.round(record.bg.g) : 'c',
      record.bg ? Math.round(record.bg.b) : 'c',
      record.large ? 1 : 0,
      record.icon ? 1 : 0,
    ].join('|');
    if (seen.has(key)) return;
    seen.add(key);
    records.push(record);
  };

  const elements = document.querySelectorAll('body *');
  elements.forEach((el, index) => {
    if (!visible(el)) return;
    const style = getComputedStyle(el);
    const direct = [...el.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim()).map((node) => node.textContent.trim()).join(' ');
    const isIcon = el.classList.contains('material-symbols-outlined') || el.getAttribute('role') === 'img';
    const placeholder = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? (el.getAttribute('placeholder') || '') : '';
    if (!direct && !placeholder && !isIcon) {
      const borderWidth = Number.parseFloat(style.borderTopWidth || '0');
      const border = parse(style.borderTopColor);
      if (borderWidth >= 1 && border && border.a > 0.2 && style.borderTopStyle !== 'none') {
        const bgInfo = opaqueBackground(el);
        if (!bgInfo.complex && bgInfo.color) {
          push({
            kind: 'border',
            text: 'border',
            className: String(el.className || '').slice(0, 180),
            tag: el.tagName.toLowerCase(),
            selector: pathFor(el),
            fg: { r: border.r, g: border.g, b: border.b },
            bg: { r: bgInfo.color.r, g: bgInfo.color.g, b: bgInfo.color.b },
            complex: false,
            fontSize: borderWidth,
            fontWeight: 400,
            large: false,
            icon: true,
            id: '',
          });
        }
      }
      return;
    }

    const placeholderStyle = placeholder ? parse(getComputedStyle(el, '::placeholder').color) : null;
    const fgParsed = placeholder && !direct && placeholderStyle ? placeholderStyle : parse(style.color);
    if (!fgParsed) return;
    const fontSize = Number.parseFloat(style.fontSize || '16');
    const fontWeight = Number.parseInt(style.fontWeight || '400', 10);
    const large = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
    const bgInfo = opaqueBackground(el);
    const rect = el.getBoundingClientRect();
    const complex = bgInfo.complex || (!bgInfo.covered && overlapsImage(rect));
    let fg = { r: fgParsed.r, g: fgParsed.g, b: fgParsed.b };
    let bg = null;
    if (!complex && bgInfo.color) {
      const opacity = bgInfo.opacity === undefined ? 1 : bgInfo.opacity;
      const faded = { ...fgParsed, a: (fgParsed.a === undefined ? 1 : fgParsed.a) * opacity };
      fg = blend(faded, bgInfo.color);
      bg = { r: bgInfo.color.r, g: bgInfo.color.g, b: bgInfo.color.b };
    }
    const id = `c${index}`;
    if (complex) el.setAttribute('data-contrast-id', id);
    const sample = (direct || placeholder || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80);
    push({
      kind: placeholder && !direct ? 'placeholder' : 'text',
      text: sample,
      className: String(el.className || '').slice(0, 180),
      tag: el.tagName.toLowerCase(),
      selector: pathFor(el),
      fg,
      bg,
      complex,
      fontSize,
      fontWeight,
      large,
      icon: isIcon,
      id: complex ? id : '',
      rect: {
        x: rect.left + window.scrollX,
        y: rect.top + window.scrollY,
        width: rect.width,
        height: rect.height,
      },
    });

    if (placeholder && direct) {
      const ph = parse(getComputedStyle(el, '::placeholder').color);
      if (ph && !complex && bg) {
        push({
          kind: 'placeholder',
          text: placeholder.slice(0, 80),
          className: String(el.className || '').slice(0, 180),
          tag: el.tagName.toLowerCase(),
          selector: pathFor(el),
          fg: blend(ph, bg),
          bg,
          complex: false,
          fontSize,
          fontWeight,
          large: false,
          icon: false,
          id: '',
        });
      }
    }
  });
  return records;
};

function sampleRegion(png, scale, region, fg) {
  const x0 = Math.max(0, Math.floor(region.x * scale));
  const y0 = Math.max(0, Math.floor(region.y * scale));
  const x1 = Math.min(png.width, Math.ceil((region.x + region.width) * scale));
  const y1 = Math.min(png.height, Math.ceil((region.y + region.height) * scale));
  let worst = null;
  let worstRatio = Infinity;
  const step = Math.max(1, Math.floor(Math.sqrt(Math.max(1, (x1 - x0) * (y1 - y0)) / 2500)));
  for (let y = y0; y < y1; y += step) {
    for (let x = x0; x < x1; x += step) {
      const i = (y * png.width + x) * 4;
      if (png.pixels[i + 3] < 16) continue;
      const bg = { r: png.pixels[i], g: png.pixels[i + 1], b: png.pixels[i + 2] };
      const ratio = contrastRatio(fg, bg);
      if (ratio < worstRatio) {
        worstRatio = ratio;
        worst = bg;
      }
    }
  }
  return worst ? { bg: worst, ratio: worstRatio } : null;
}

export async function collectPageContrast(page, meta) {
  const records = await page.evaluate(COLLECT);
  const complex = records.filter((record) => record.complex && record.rect);
  const sampled = new Map();
  if (complex.length) {
    const style = await page.addStyleTag({
      content: 'body * , body *::placeholder { color: transparent !important; -webkit-text-fill-color: transparent !important; text-shadow: none !important; }',
    });
    const viewport = page.viewportSize() || { width: 1440, height: 900 };
    const pageHeight = await page.evaluate(() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));
    const slice = Math.max(400, viewport.height - 40);
    for (let top = 0; top < pageHeight; top += slice) {
      await page.evaluate((y) => window.scrollTo(0, y), top);
      const shot = await page.screenshot({ animations: 'disabled' });
      const png = decodePng(shot);
      const scale = png.width / viewport.width;
      for (let index = 0; index < complex.length; index += 1) {
        const record = complex[index];
        const viewY = record.rect.y - top;
        const viewX = record.rect.x;
        if (viewY + record.rect.height < 0 || viewY > viewport.height) continue;
        if (viewX + record.rect.width < 0 || viewX > viewport.width) continue;
        const raw = {
          x: Math.max(0, viewX),
          y: Math.max(0, viewY),
          width: Math.min(record.rect.width, viewport.width - Math.max(0, viewX)),
          height: Math.min(record.rect.height, viewport.height - Math.max(0, viewY)),
        };
        const pad = Math.min(6, Math.floor(Math.min(raw.width, raw.height) / 4));
        const region = {
          x: raw.x + pad,
          y: raw.y + pad,
          width: Math.max(2, raw.width - pad * 2),
          height: Math.max(2, raw.height - pad * 2),
        };
        const worst = sampleRegion(png, scale, region, record.fg);
        if (!worst) continue;
        const previous = sampled.get(index);
        if (!previous || worst.ratio < previous.ratio) sampled.set(index, worst);
      }
      if (top + slice >= pageHeight) break;
      if (top > 12000) break;
    }
    await style.evaluate((node) => node.remove()).catch(async () => {
      await page.evaluate(() => {
        document.querySelectorAll('style').forEach((node) => {
          if (node.textContent && node.textContent.includes('-webkit-text-fill-color: transparent')) node.remove();
        });
      });
    });
    await page.evaluate(() => window.scrollTo(0, 0));
  }

  const measured = [];
  let complexIndex = 0;
  for (const record of records) {
    let bg = record.bg;
    let ratio = null;
    if (record.complex) {
      const worst = sampled.get(complexIndex);
      complexIndex += 1;
      if (!worst) continue;
      bg = worst.bg;
      ratio = worst.ratio;
    }
    if (!bg) continue;
    if (ratio === null) ratio = contrastRatio(record.fg, bg);
    const threshold = record.kind === 'border' || record.icon || record.large ? 3 : 4.5;
    measured.push({
      ...meta,
      state: meta.state || 'rest',
      kind: record.kind,
      text: record.text,
      className: record.className,
      tag: record.tag,
      selector: record.selector,
      fg: hex(record.fg),
      bg: hex(bg),
      ratio: Math.round(ratio * 100) / 100,
      threshold,
      pass: ratio + 0.05 >= threshold,
      fontSize: record.fontSize,
      complex: Boolean(record.complex),
    });
  }
  return measured;
}

export function summarize(rows) {
  const failures = rows.filter((row) => !row.pass);
  const worst = [...failures].sort((a, b) => a.ratio - b.ratio).slice(0, 10);
  return {
    pairsChecked: rows.length,
    failures: failures.length,
    passes: rows.length - failures.length,
    worst,
    failures,
  };
}
