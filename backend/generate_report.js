const {
    Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
    AlignmentType, LevelFormat, BorderStyle, WidthType, ShadingType,
    ImageRun, VerticalAlign, Footer
  } = require('./node_modules/docx');
  const fs   = require('fs');
  const path = require('path');
  
  const input = JSON.parse(fs.readFileSync('/dev/stdin', 'utf8'));
  const { title, metadata, impact, what_happened, why_it_matters,
          tell_me_more, sources, logo_path, output_path } = input;
  
  const NAVY       = "1B2A4A";
  const NAVY_TEXT  = "1B2A4A";
  const DARK_TEXT  = "1A1A1A";
  const GRAY_TEXT  = "595959";
  const WHITE      = "FFFFFF";
  const RULE_COLOR = "CCCCCC";
  
  const noBorder  = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
  
  function bullet(text, level = 0) {
    return new Paragraph({
      numbering: { reference: "bullets", level },
      children: [new TextRun({ text, font: "Arial", size: 20, color: DARK_TEXT })],
      spacing: { after: 80 },
    });
  }
  
  function sectionHeading(text) {
    return new Paragraph({
      children: [new TextRun({ text, font: "Arial", size: 24, bold: true, color: NAVY_TEXT })],
      spacing: { before: 280, after: 120 },
    });
  }
  
  function horizontalRule() {
    return new Paragraph({
      children: [new TextRun("")],
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE_COLOR, space: 1 } },
      spacing: { before: 0, after: 160 },
    });
  }
  
  function spacer(after = 120) {
    return new Paragraph({ children: [new TextRun("")], spacing: { after } });
  }
  
  // ── Load logo — read actual PNG dimensions for correct aspect ratio ────────────
  let logoRun = null;
  if (logo_path && fs.existsSync(logo_path)) {
    const logoData = fs.readFileSync(logo_path);
    // PNG dimensions are at bytes 16-24 in the header
    const pngW = logoData.readUInt32BE(16);
    const pngH = logoData.readUInt32BE(20);
    const ratio = pngW / pngH;
    // Fit into a 48px tall space, scale width by ratio
    const displayH = 48;
    const displayW = Math.round(displayH * ratio);
    logoRun = new ImageRun({
      data: logoData,
      transformation: { width: displayW, height: displayH },
      type: "png",
    });
  }
  
  // ── Helper: metadata line (only render if value is non-empty) ──────────────────
  function metaLine(label, value) {
    if (!value || !value.trim()) return null;
    return new Paragraph({
      children: [
        new TextRun({ text: label + " ", font: "Arial", size: 20, bold: true, color: DARK_TEXT }),
        new TextRun({ text: value, font: "Arial", size: 20, color: DARK_TEXT }),
      ],
      spacing: { after: 80 },
    });
  }
  
  const children = [];
  
  // ── Header table ──────────────────────────────────────────────────────────────
  const headerCell = {
    borders: noBorders,
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    margins: { top: 120, bottom: 120, left: 160, right: 160 },
    verticalAlign: VerticalAlign.CENTER,
  };
  
  children.push(new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [1400, 6360, 1600],
    rows: [new TableRow({
      children: [
        new TableCell({
          ...headerCell,
          width: { size: 1400, type: WidthType.DXA },
          children: [new Paragraph({
            alignment: AlignmentType.LEFT,
            children: logoRun
              ? [logoRun]
              : [new TextRun({ text: "abbvie", font: "Arial", size: 24, bold: true, color: WHITE })],
          })],
        }),
        new TableCell({
          ...headerCell,
          width: { size: 6360, type: WidthType.DXA },
          children: [
            new Paragraph({
              alignment: AlignmentType.LEFT,
              children: [new TextRun({ text: "Immunology", font: "Arial", size: 20, bold: true, color: WHITE })],
              spacing: { after: 40 },
            }),
            new Paragraph({
              alignment: AlignmentType.LEFT,
              children: [new TextRun({ text: "Competitive Intelligence Update", font: "Arial", size: 26, bold: true, color: WHITE })],
            }),
          ],
        }),
        new TableCell({
          ...headerCell,
          width: { size: 1600, type: WidthType.DXA },
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [new TextRun({ text: "Brought to you by:", font: "Arial", size: 14, color: WHITE })],
              spacing: { after: 20 },
            }),
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [new TextRun({ text: "APEX & IMABI CI", font: "Arial", size: 16, bold: true, color: WHITE })],
            }),
          ],
        }),
      ],
    })],
  }));
  
  children.push(spacer(200));
  
  // ── Title ─────────────────────────────────────────────────────────────────────
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({
      text: title || "Synthesized Intelligence Report",
      font: "Arial", size: 28, bold: true, color: NAVY_TEXT, underline: {},
    })],
    spacing: { after: 200 },
  }));
  
  // ── Metadata two-column — only show rows with values ─────────────────────────
  const today = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  const metaCell = { borders: noBorders, margins: { top: 60, bottom: 60, left: 0, right: 0 } };
  
  const leftLines  = [metaLine("Company:", metadata?.company), metaLine("Drug:", metadata?.drug)].filter(Boolean);
  const rightLines = [metaLine("Date:", metadata?.date || today), metaLine("Source(s):", sources?.join(", "))].filter(Boolean);
  
  if (leftLines.length || rightLines.length) {
    children.push(new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [4680, 4680],
      rows: [new TableRow({
        children: [
          new TableCell({
            ...metaCell,
            width: { size: 4680, type: WidthType.DXA },
            children: leftLines.length ? leftLines : [new Paragraph({ children: [new TextRun("")] })],
          }),
          new TableCell({
            ...metaCell,
            width: { size: 4680, type: WidthType.DXA },
            children: rightLines.length ? rightLines : [new Paragraph({ children: [new TextRun("")] })],
          }),
        ],
      })],
    }));
  }
  
  children.push(horizontalRule());
  
  // ── What Happened ─────────────────────────────────────────────────────────────
  if (what_happened?.length) {
    children.push(sectionHeading("What happened:"));
    what_happened.forEach(item => children.push(bullet(item)));
    children.push(spacer(80));
  }
  
  // ── Impact ────────────────────────────────────────────────────────────────────
  const impactLevel = (impact || "MEDIUM").toUpperCase();
  const impactColor = impactLevel === "HIGH"   ? "C00000"
                    : impactLevel === "MEDIUM" ? "C55A11"
                    :                           "375623";
  children.push(new Paragraph({
    children: [
      new TextRun({ text: "Impact (CI PoV): ", font: "Arial", size: 24, bold: true, color: NAVY_TEXT }),
      new TextRun({ text: impactLevel, font: "Arial", size: 24, bold: true, color: impactColor }),
    ],
    spacing: { before: 160, after: 120 },
  }));
  
  // ── Why It Matters ────────────────────────────────────────────────────────────
  if (why_it_matters?.length) {
    why_it_matters.forEach(item => children.push(bullet(item)));
    children.push(spacer(80));
  }
  
  // ── Tell Me More ──────────────────────────────────────────────────────────────
  if (tell_me_more?.length) {
    children.push(sectionHeading("Tell me more:"));
    tell_me_more.forEach(item => children.push(bullet(item)));
    children.push(spacer(80));
  }
  
  // ── Sources ───────────────────────────────────────────────────────────────────
  if (sources?.length) {
    children.push(horizontalRule());
    children.push(new Paragraph({
      children: [new TextRun({ text: "Sources:", font: "Arial", size: 18, bold: true, color: GRAY_TEXT })],
      spacing: { after: 80 },
    }));
    sources.forEach(s => children.push(new Paragraph({
      children: [new TextRun({ text: s, font: "Arial", size: 18, color: GRAY_TEXT })],
      spacing: { after: 60 },
    })));
  }
  
  // ── Assemble ──────────────────────────────────────────────────────────────────
  const doc = new Document({
    numbering: {
      config: [{
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25CB", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
        ],
      }],
    },
    styles: { default: { document: { run: { font: "Arial", size: 20 } } } },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 720, right: 1080, bottom: 1080, left: 1080 },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({
              text: "CONFIDENTIAL | AbbVie Internal Use Only",
              font: "Arial", size: 16, color: GRAY_TEXT, italics: true,
            })],
          })],
        }),
      },
      children,
    }],
  });
  
  Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync(output_path, buffer);
    console.log("OK:" + output_path);
  }).catch(err => {
    console.error("ERROR:" + err.message);
    process.exit(1);
  });