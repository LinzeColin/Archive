const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle,
  ShadingType, Footer, PageNumber, HeadingLevel, TableLayoutType, VerticalAlign } = require('docx');
const { imageSize } = (() => { try { return require('image-size'); } catch (e) { return {}; } })();

const doc = JSON.parse(fs.readFileSync('doc.json', 'utf8'));
const FONT = 'Calibri';
const TEXTW = 9412;           // 16.6 cm in DXA
const PT = (x) => Math.round(x * 2);   // half-points
const INK = '1F1F1F', GREY = '595959', RULE = '404040';

function pngSize(file) {
  const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function runs(text, opts = {}) {
  const out = []; const re = /(<b>.*?<\/b>|<i>.*?<\/i>)/g; let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...opts }));
    const inner = m[0].replace(/<\/?[bi]>/g, '');
    out.push(new TextRun({ text: inner, bold: m[0].startsWith('<b>') || opts.bold, italics: m[0].startsWith('<i>'), ...opts }));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...opts }));
  return out;
}
const NONE = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
function cell(text, { width, bold = false, fill, align = AlignmentType.LEFT, top, bottom, size = 8.5, color = INK }) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, verticalAlign: VerticalAlign.TOP,
    margins: { top: 30, bottom: 30, left: 70, right: 70 },
    shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined,
    borders: { top: top || NONE, bottom: bottom || NONE, left: NONE, right: NONE },
    children: [new Paragraph({ alignment: align, spacing: { before: 0, after: 0, line: 240 }, children: [new TextRun({ text: String(text), bold, font: FONT, size: PT(size), color })] })],
  });
}
function table(t) {
  const widths = t.widths.map(p => Math.round(TEXTW * p / t.widths.reduce((a, b) => a + b, 0)));
  const diff = TEXTW - widths.reduce((a, b) => a + b, 0); widths[0] += diff;
  const thick = { style: BorderStyle.SINGLE, size: 8, color: RULE }, thin = { style: BorderStyle.SINGLE, size: 4, color: RULE }, hair = { style: BorderStyle.SINGLE, size: 2, color: 'BFBFBF' };
  const numFrom = t.num_from ?? 99;
  const fs = t.font || 8.5;
  const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: t.head.map((h, j) => cell(h, { width: widths[j], bold: true, fill: 'F2F2F2', top: thick, bottom: thin, size: fs, align: j >= numFrom ? AlignmentType.RIGHT : AlignmentType.LEFT })) })];
  t.rows.forEach((r, i) => {
    const last = i === t.rows.length - 1; const grpTop = t.group_every && i > 0 && i % t.group_every === 0;
    rows.push(new TableRow({ cantSplit: true, children: r.map((c, j) => {
      let color = INK; if (t.group_every && j === 1) color = c === 'Luxury' ? 'B34A1E' : (c === 'Non-luxury' ? '1F5DA8' : INK);
      return cell(c, { width: widths[j], bold: (t.group_every && j === 0 && c !== ''), align: j >= numFrom ? AlignmentType.RIGHT : AlignmentType.LEFT,
        top: grpTop ? hair : undefined, bottom: last ? thick : undefined, color, size: fs });
    }) }));
  });
  const out = [
    new Paragraph({ keepNext: true, spacing: { before: t.font ? 100 : 160, after: 60 }, children: runs(t.title.replace(/^(Table [A0-9]+)\s+/, '<b>$1</b>  '), { font: FONT, size: PT(9) }) }),
    new Table({ width: { size: TEXTW, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED, rows }),
  ];
  if (t.note) out.push(new Paragraph({ spacing: { before: 40, after: 120 }, children: [new TextRun({ text: t.note, font: FONT, size: PT(7.5), color: GREY })] }));
  else out.push(new Paragraph({ spacing: { before: 0, after: 80 }, children: [] }));
  return out;
}
function figure(key) {
  const [file, cap, wcm] = doc.figs[key]; const { w, h } = pngSize(file);
  const wpx = wcm / 2.54 * 96; const hpx = wpx * h / w;
  const capM = cap.match(/^(Figure \d+)\s+(.*)$/);
  return [
    new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, spacing: { before: 160, after: 40 }, children: [new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width: Math.round(wpx), height: Math.round(hpx) },
      altText: { title: capM[1], description: capM[2], name: capM[1] } })] }),
    new Paragraph({ spacing: { before: 0, after: 160 }, children: [new TextRun({ text: capM[1] + '  ', bold: true, font: FONT, size: PT(8.5) }), ...runs(capM[2], { font: FONT, size: PT(8.5), color: '333333' })] }),
  ];
}
const children = [];
children.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: doc.title, bold: true, font: FONT, size: PT(17), color: INK })] }));
children.push(new Paragraph({ spacing: { after: 30 }, children: [new TextRun({ text: doc.sub, font: FONT, size: PT(9.5), color: GREY })] }));
children.push(new Paragraph({ spacing: { after: 200 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 6 } },
  children: [new TextRun({ text: `Word count: ${doc.wc} (headings included; tables, figures, captions, notes, references and appendix excluded)`, font: FONT, size: PT(9), color: GREY })] }));
for (const [kind, val] of doc.body) {
  if (kind === 'h1') children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, spacing: { before: 240, after: 80 }, children: [new TextRun({ text: val.replace('  ', '   '), bold: true, font: FONT, size: PT(13), color: INK })] }));
  else if (kind === 'h2') children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, spacing: { before: 160, after: 60 }, children: [new TextRun({ text: val.replace('  ', '   '), bold: true, font: FONT, size: PT(11), color: INK })] }));
  else if (kind === 'p') children.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { before: 0, after: 120, line: 264 }, children: runs(val, { font: FONT, size: PT(10.5), color: INK }) }));
  else if (kind === 'table') children.push(...table(doc.tables[val]));
  else if (kind === 'fig') children.push(...figure(val));
}
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, spacing: { before: 240, after: 80 }, children: [new TextRun({ text: 'References', bold: true, font: FONT, size: PT(13), color: INK })] }));
for (const ref of doc.refs) {
  children.push(new Paragraph({ indent: { left: 400, hanging: 400 }, spacing: { after: 80, line: 252 },
    children: ref.map(([t, it]) => new TextRun({ text: t, italics: it, font: FONT, size: PT(10), color: INK })) }));
}
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, spacing: { before: 240, after: 40 }, children: [new TextRun({ text: 'Appendix', bold: true, font: FONT, size: PT(13), color: INK })] }));
for (const k of doc.appx) children.push(...table(doc.tables[k]));

const document = new Document({
  creator: '', lastModifiedBy: '', title: doc.title, description: '',
  styles: {
    default: { document: { run: { font: FONT, size: PT(10.5), color: INK } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: PT(13), bold: true, color: INK }, paragraph: { outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: PT(11), bold: true, color: INK }, paragraph: { outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1247, right: 1247, footer: 567 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: 'Page ', font: FONT, size: PT(8.5), color: GREY }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: PT(8.5), color: GREY }),
      new TextRun({ text: ' of ', font: FONT, size: PT(8.5), color: GREY }), new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: PT(8.5), color: GREY })] })] }) },
    children,
  }],
});
Packer.toBuffer(document).then(buf => { fs.writeFileSync(process.argv[2] || 'report_v2.docx', buf); console.log('docx written'); });
