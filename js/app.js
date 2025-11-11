function getInlineData() {
  const el = document.getElementById('data-json');
  if (!el) return null;
  try { return JSON.parse(el.textContent); } catch (_) { return null; }
}

function el(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text != null) n.textContent = text;
  return n;
}

// Absolute path to your vault's 1000_assets for fallback viewing
const VAULT_ASSETS_ROOT = 'L:/我的雲端硬碟/GD_ObsidianVault/1000_assets';

function resolveImageSrc(src) {
  if (!src) return '';
  let s = String(src).trim();
  // Normalize to site folder under images/1000_assets
  if (/^1000_assets\//.test(s)) {
    return `images/${s}`;
  }
  // Bare filename → assume under images/1000_assets/
  if (!/\//.test(s)) {
    return `images/1000_assets/${s}`;
  }
  // Default: still try under images/1000_assets/<basename>
  const base = s.split('/').pop();
  return `images/1000_assets/${base}`;
}

function candidateImageSrcs(src) {
  const primary = resolveImageSrc(src);
  const base = String(src || '').split('/').pop();
  const vaultPath = `${VAULT_ASSETS_ROOT}/${base}`;
  const vaultUrl = `file:///${vaultPath.replace(/\\/g,'/').replace(/:/,':')}`;
  return [primary, vaultUrl];
}

function formatHM(val) {
  if (val == null) return '';
  const s = String(val).trim();
  if (/^\d{1,4}$/.test(s)) {
    let digits = s.replace(/\D/g, '');
    if (digits.length === 3) digits = '0' + digits;
    if (digits.length === 4) {
      const hh = parseInt(digits.slice(0, 2), 10);
      const mm = digits.slice(2);
      return `${hh}:${mm}`;
    }
  }
  // Already formatted (e.g., 10:30), return as-is
  return s;
}

function parseTimeToMinutes(val) {
  if (val == null) return null;
  let s = String(val).trim();
  if (!s) return null;
  // Normalize "HH:MM" or "H:MM"
  const colon = /^\s*(\d{1,2})\s*:\s*(\d{2})\s*$/;
  const m1 = s.match(colon);
  if (m1) {
    const hh = parseInt(m1[1], 10);
    const mm = parseInt(m1[2], 10);
    if (!Number.isNaN(hh) && !Number.isNaN(mm)) return hh * 60 + mm;
    return null;
  }
  // Normalize digits: HMM / HHMM
  const digits = s.replace(/\D/g, '');
  if (!digits) return null;
  if (digits.length === 3) {
    // e.g., 930 -> 09:30
    const hh = parseInt(digits.slice(0, 1), 10);
    const mm = parseInt(digits.slice(1), 10);
    if (!Number.isNaN(hh) && !Number.isNaN(mm)) return hh * 60 + mm;
  } else if (digits.length === 4) {
    const hh = parseInt(digits.slice(0, 2), 10);
    const mm = parseInt(digits.slice(2), 10);
    if (!Number.isNaN(hh) && !Number.isNaN(mm)) return hh * 60 + mm;
  }
  return null;
}

function renderDayTo(root, day) {
  const dayBox = el('section', 'day');
  const title = el('div', 'date-title', day.date || '');
  dayBox.appendChild(title);

  // Fitness notes directly under the date title
  if (Array.isArray(day.fitness_notes) && day.fitness_notes.length) {
    const fitList = el('ul', 'fitness-notes list');
    day.fitness_notes.forEach(t => {
      if (!t) return;
      fitList.appendChild(el('li', null, String(t)));
    });
    dayBox.appendChild(fitList);
  }

  // Sleep card
  const sleepCard = el('section', 'card sleep-card');
  let sleepTitle = el('h2', 'card-title', '💤 睡覺時間');
  const sleepList = el('ul', 'list');
  const sleepSegments = [];
  (day.sleep || []).forEach(s => {
    const hoursPart = (s.hours != null && s.hours !== '') ? `${s.hours} 小時` : '';
    const times = [];
    if (s.start) times.push(s.start);
    if (s.end) times.push(s.end);
    const rangePart = times.length === 2 ? `${times[0]} - ${times[1]}` : times.join(' - ');
    if (hoursPart || rangePart) sleepSegments.push({ hoursPart, rangePart });
  });
  if (sleepSegments.length) {
    const li = el('li');
    sleepSegments.forEach((seg, idx) => {
      if (idx > 0) li.appendChild(document.createTextNode(' '));
      li.appendChild(document.createTextNode('⏰ '));
      if (seg.hoursPart) {
        const strong = el('span', 'sleep-hours', seg.hoursPart);
        li.appendChild(strong);
      }
      if (seg.hoursPart && seg.rangePart) li.appendChild(document.createTextNode(' | '));
      if (seg.rangePart) li.appendChild(document.createTextNode(seg.rangePart));
    });
    sleepList.appendChild(li);
  }
  // Add late sleep indicator by time (ignore checkbox): any sleep start after midnight counts
  const lateSleep = (day.sleep || []).some(s => {
    const m = parseTimeToMinutes(s && s.start);
    return m != null && m >= 0 && m < 360; // 00:00~05:59 視為跨日入睡 → 晚睡
  });
  if (lateSleep) {
    const warn = el('span');
    warn.textContent = '  ❌ 晚睡';
    sleepTitle.appendChild(warn);
  }
  // For wide screens: left column label for Sleep (kept together with card title for mobile)
  const sleepLabel = el('div', 'row-label row-label--sleep', '💤 睡覺時間');
  if (lateSleep) {
    const warn2 = el('span');
    warn2.textContent = '  ❌ 晚睡';
    sleepLabel.appendChild(warn2);
  }
  dayBox.appendChild(sleepLabel);
  sleepCard.appendChild(sleepTitle);
  sleepCard.appendChild(sleepList);
  dayBox.appendChild(sleepCard);

  // Exercise card
  const exList = el('ul', 'list');
  (day.exercise || []).forEach(e => {
    const li = el('li');
    const duration = (e.duration || '').trim();
    const start = (e.start || '').trim();
    const typeText = (e.type || '').trim();
    const minutes = /^\d+$/.test(duration) ? `${duration}分鐘` : duration;
    const startPadded = start ? start.padStart(4, '0') : '';
    const startFmt = /^\d{4}$/.test(startPadded) ? `${parseInt(startPadded.slice(0,2),10)}:${startPadded.slice(2)}` : start;
    const segs = [];
    if (typeText) segs.push(typeText);
    if (minutes) segs.push(`⏰ ${minutes}`);
    if (startFmt) segs.push(startFmt);
    li.textContent = segs.join(' | ');
    exList.appendChild(li);
  });
  if (exList.children.length) {
    // Left column label for Exercise in row 2
    const exLabel = el('div', 'row-label row-label--exercise', '🏃‍♀️ 運動');
    dayBox.appendChild(exLabel);
    const exCard = el('section', 'card exercise-card');
    exCard.appendChild(el('h2', 'card-title', '🏃‍♀️ 運動'));
    exCard.appendChild(exList);
    dayBox.appendChild(exCard);
  }

  // Diet card
  const dietList = el('ul', 'list');
  (day.diet || []).forEach(d => {
    const li = el('li', 'diet-item');
    const timeText = d.time ? `⏰ ${formatHM(d.time)}` : '';
    const itemText = d.item ? `${d.item}` : '';
    const middle = timeText && itemText ? ' | ' : '';
    li.textContent = `${timeText}${middle}${itemText}`;
    dietList.appendChild(li);
  });
  if (dietList.children.length) {
    const dietCard = el('section', 'card diet-card');
    const dietTitle = el('h2', 'card-title', '🍎 飲食');
    // Add late eating indicator by time (ignore checkbox): any diet time >= 20:00
    const lateEating = (day.diet || []).some(d => {
      const m = parseTimeToMinutes(d && d.time);
      return m != null && m >= 20 * 60;
    });
    if (lateEating) {
      const warn = el('span');
      warn.textContent = '  ❌ 八點後進食';
      dietTitle.appendChild(warn);
    }
    // Left column label for Diet with same late badge
    const dietLabel = el('div', 'row-label row-label--diet', '🍎 飲食');
    if (lateEating) {
      const warn2 = el('span');
      warn2.textContent = '  ❌ 八點後進食';
      dietLabel.appendChild(warn2);
    }
    dayBox.appendChild(dietLabel);
    dietCard.appendChild(dietTitle);
    dietCard.appendChild(dietList);
    dayBox.appendChild(dietCard);
  }

  // Photos card
  const photoStrip = el('div', 'photo-strip');
  const imgsAgg = [];
  const seenBases = new Set();
  (day.diet || []).forEach(d => (d.images || []).forEach(src => {
    const base = String(src || '').split('/').pop();
    if (!base || seenBases.has(base)) return;
    seenBases.add(base);
    imgsAgg.push({ src, alt: '' });
  }));
  imgsAgg.forEach(({ src, alt }) => {
    const img = new Image();
    img.alt = alt;
    const candidates = candidateImageSrcs(src);
    let idx = 0;
    function tryNext() {
      if (idx >= candidates.length) {
        img.remove();
        return;
      }
      img.src = candidates[idx++];
    }
    img.onerror = tryNext;
    tryNext();
    photoStrip.appendChild(img);
  });
  if (photoStrip.children.length) {
    const photoCard = el('section', 'photo-card card');
    photoCard.appendChild(photoStrip);
    dayBox.appendChild(photoCard);
  }

  root.appendChild(dayBox);
}

function render(data) {
  const root = document.getElementById('days-root');
  root.innerHTML = '';
  const toc = document.getElementById('toc');
  if (toc) toc.innerHTML = '';
  if (data && Array.isArray(data.days) && data.days.length) {
    data.days.forEach(day => {
      // anchor id
      const anchorId = `day-${day.date}`;
      // render day
      renderDayTo(root, day);
      // assign id to last added day section
      const last = root.lastElementChild;
      if (last) last.id = anchorId;
      // add toc link
      if (toc) {
        const a = document.createElement('a');
        a.href = `#${anchorId}`;
        a.textContent = day.date;
        toc.appendChild(a);
      }
    });
    return;
  }
  if (data && data.date) {
    renderDayTo(root, data);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const data = getInlineData();
  if (data) {
    // Set header title to date range
    const headerTitle = document.querySelector('.site-header h1');
    if (headerTitle) {
      if (Array.isArray(data.days) && data.days.length) {
        const start = data.days[0].date;
        const end = data.days[data.days.length - 1].date;
        headerTitle.textContent = `${start} ~ ${end}`;
        document.title = `${start} ~ ${end}`;
      } else if (data.date) {
        headerTitle.textContent = data.date;
        document.title = data.date;
      }
    }
    render(data);
  }
});


