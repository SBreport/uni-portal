const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, HeadingLevel, LevelFormat,
  Header, Footer, PageNumber, PageBreak
} = require("docx");

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: "2563EB", type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, bold: true, color: "FFFFFF", font: "Arial", size: 20 })]
    })]
  });
}

function bodyCell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    margins: cellMargins,
    children: [new Paragraph({
      alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text, font: "Arial", size: 20, ...(opts.bold ? { bold: true } : {}) })]
    })]
  });
}

function labelValueRow(label, value, labelW = 2400, valueW = 6960) {
  return new TableRow({
    children: [
      new TableCell({
        borders,
        width: { size: labelW, type: WidthType.DXA },
        shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
        margins: cellMargins,
        children: [new Paragraph({
          children: [new TextRun({ text: label, bold: true, font: "Arial", size: 20 })]
        })]
      }),
      new TableCell({
        borders,
        width: { size: valueW, type: WidthType.DXA },
        margins: cellMargins,
        children: [new Paragraph({
          children: [new TextRun({ text: value, font: "Arial", size: 20 })]
        })]
      })
    ]
  });
}

function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ heading: level, spacing: { before: 300, after: 150 },
    children: [new TextRun({ text, font: "Arial" })] });
}

function bodyText(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 100 },
    children: [new TextRun({ text, font: "Arial", size: 20, ...opts })]
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "1E293B" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "2563EB" },
        paragraph: { spacing: { before: 240, after: 150 }, outlineLevel: 1 } },
    ]
  },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
    }]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "NAS Docker Environment Setup Request", font: "Arial", size: 16, color: "94A3B8", italics: true })]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Page ", font: "Arial", size: 16, color: "94A3B8" }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "94A3B8" })
          ]
        })]
      })
    },
    children: [
      // ── Title ──
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [new TextRun({ text: "NAS Docker \uD658\uACBD \uAD6C\uC131 \uC694\uCCAD\uC11C", font: "Arial", size: 36, bold: true, color: "1E293B" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: [new TextRun({ text: "\uC720\uC564\uC544\uC774\uC758\uC6D0 \uC7A5\uBE44 \uD604\uD669 \uAD00\uB9AC \uC2DC\uC2A4\uD15C", font: "Arial", size: 22, color: "64748B" })]
      }),

      // ── 1. \uC694\uCCAD \uAC1C\uC694 ──
      heading("1. \uC694\uCCAD \uAC1C\uC694"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 6960],
        rows: [
          labelValueRow("\uC694\uCCAD\uC77C", "2026\uB144 3\uC6D4 12\uC77C"),
          labelValueRow("\uC694\uCCAD \uBD80\uC11C", "\uB9C8\uCF00\uD305\uD300"),
          labelValueRow("\uBAA9\uC801", "\uC9C0\uC810\uBCC4 \uBCF4\uC720\uC7A5\uBE44 \uD604\uD669 \uAD00\uB9AC \uC6F9 \uC560\uD50C\uB9AC\uCF00\uC774\uC158 \uBC30\uD3EC"),
          labelValueRow("\uB300\uC0C1 \uC2DC\uC2A4\uD15C", "Synology NAS (Docker \uD328\uD0A4\uC9C0 \uC124\uCE58 \uC644\uB8CC)"),
          labelValueRow("\uC6B4\uC601 \uBC94\uC704", "44\uAC1C \uC9C0\uC810, \uC7A5\uBE44 1,800\uC5EC\uAC74 \uB370\uC774\uD130 \uAD00\uB9AC"),
        ]
      }),

      // ── 2. \uD544\uC694 \uC0AC\uD56D ──
      heading("2. \uD544\uC694 \uC0AC\uD56D"),
      heading("2.1 Docker \uCEE8\uD14C\uC774\uB108 \uC124\uC815", HeadingLevel.HEADING_2),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2000, 2200, 5160],
        rows: [
          new TableRow({ children: [headerCell("\uD56D\uBAA9", 2000), headerCell("\uAC12", 2200), headerCell("\uC124\uBA85", 5160)] }),
          new TableRow({ children: [
            bodyCell("\uCEE8\uD14C\uC774\uB108\uBA85", 2000), bodyCell("uni-equipment", 2200),
            bodyCell("\uC7A5\uBE44 \uD604\uD669 \uAD00\uB9AC \uC571", 5160)] }),
          new TableRow({ children: [
            bodyCell("\uC774\uBBF8\uC9C0", 2000), bodyCell("python:3.11-slim", 2200),
            bodyCell("Docker Hub \uACF5\uC2DD \uC774\uBBF8\uC9C0", 5160)] }),
          new TableRow({ children: [
            bodyCell("\uD3EC\uD2B8", 2000), bodyCell("8501:8501", 2200),
            bodyCell("\uC678\uBD80:8501 \u2192 \uB0B4\uBD80:8501 (Streamlit \uAE30\uBCF8 \uD3EC\uD2B8)", 5160)] }),
          new TableRow({ children: [
            bodyCell("\uBCFC\uB968 \uB9C8\uC6B4\uD2B8", 2000), bodyCell("/nas/uni-equipment", 2200),
            bodyCell("NAS \uD3F4\uB354 \u2192 \uCEE8\uD14C\uC774\uB108 /app \uACBD\uB85C\uC5D0 \uB9C8\uC6B4\uD2B8", 5160)] }),
          new TableRow({ children: [
            bodyCell("\uC7AC\uC2DC\uC791 \uC815\uCC45", 2000), bodyCell("always", 2200),
            bodyCell("NAS \uC7AC\uBD80\uD305 \uC2DC \uC790\uB3D9 \uC2DC\uC791", 5160)] }),
          new TableRow({ children: [
            bodyCell("\uBA54\uBAA8\uB9AC \uC81C\uD55C", 2000), bodyCell("512MB", 2200),
            bodyCell("\uACBD\uB7C9 \uC571 \uAE30\uC900 \uCDA9\uBD84", 5160)] }),
        ]
      }),

      heading("2.2 \uD5A5\uD6C4 \uD655\uC7A5 \uCEE8\uD14C\uC774\uB108 (\uCC38\uACE0)", HeadingLevel.HEADING_2),
      bodyText("\uD604\uC7AC\uB294 \uC7A5\uBE44 \uAD00\uB9AC(uni-equipment)\uB9CC \uBC30\uD3EC\uD558\uBA70, \uD5A5\uD6C4 \uC544\uB798 \uCEE8\uD14C\uC774\uB108\uAC00 \uCD94\uAC00\uB420 \uC218 \uC788\uC2B5\uB2C8\uB2E4:"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2500, 1500, 5360],
        rows: [
          new TableRow({ children: [headerCell("\uCEE8\uD14C\uC774\uB108", 2500), headerCell("\uD3EC\uD2B8", 1500), headerCell("\uC6A9\uB3C4", 5360)] }),
          new TableRow({ children: [
            bodyCell("uni-equipment", 2500), bodyCell("8501", 1500, { center: true }),
            bodyCell("\uC7A5\uBE44 \uD604\uD669 \uAD00\uB9AC (\uD604\uC7AC \uC694\uCCAD)", 5360)] }),
          new TableRow({ children: [
            bodyCell("uni-events", 2500), bodyCell("8502", 1500, { center: true }),
            bodyCell("\uC774\uBCA4\uD2B8/\uC2DC\uC220 \uAD00\uB9AC (\uCD94\uD6C4)", 5360)] }),
          new TableRow({ children: [
            bodyCell("uni-marketing", 2500), bodyCell("8503", 1500, { center: true }),
            bodyCell("\uB9C8\uCF00\uD305 \uC6D0\uACE0 \uAD00\uB9AC (\uCD94\uD6C4)", 5360)] }),
          new TableRow({ children: [
            bodyCell("uni-portal", 2500), bodyCell("8500", 1500, { center: true }),
            bodyCell("\uD1B5\uD569 \uD3EC\uD138 (\uCD94\uD6C4)", 5360)] }),
        ]
      }),

      // ── 3. NAS \uD3F4\uB354 \uAD6C\uC870 ──
      heading("3. NAS \uD3F4\uB354 \uAD6C\uC870"),
      bodyText("\uC544\uB798 \uD3F4\uB354\uB97C NAS \uACF5\uC720 \uD3F4\uB354 \uB0B4\uC5D0 \uC0DD\uC131\uD574\uC8FC\uC138\uC694:"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3500, 5860],
        rows: [
          new TableRow({ children: [headerCell("\uD3F4\uB354 \uACBD\uB85C", 3500), headerCell("\uC6A9\uB3C4", 5860)] }),
          new TableRow({ children: [bodyCell("/nas/uni-equipment/", 3500), bodyCell("\uC7A5\uBE44 \uAD00\uB9AC \uC571 \uCF54\uB4DC + \uB370\uC774\uD130", 5860)] }),
          new TableRow({ children: [bodyCell("/nas/uni-equipment/data/", 3500), bodyCell("SQLite DB \uD30C\uC77C (equipment.db)", 5860)] }),
          new TableRow({ children: [bodyCell("/nas/uni-equipment/data/backups/", 3500), bodyCell("DB \uC790\uB3D9 \uBC31\uC5C5 (7\uC77C \uBCF4\uAD00)", 5860)] }),
          new TableRow({ children: [bodyCell("/nas/uni-events/ (\uCD94\uD6C4)", 3500), bodyCell("\uC774\uBCA4\uD2B8 \uAD00\uB9AC \uC571", 5860)] }),
          new TableRow({ children: [bodyCell("/nas/uni-marketing/ (\uCD94\uD6C4)", 3500), bodyCell("\uB9C8\uCF00\uD305 \uC6D0\uACE0 \uAD00\uB9AC \uC571", 5860)] }),
        ]
      }),

      // ── 4. \uC2DC\uC2A4\uD15C \uC0AC\uC591 ──
      heading("4. \uC2DC\uC2A4\uD15C \uC0AC\uC591 \uBC0F \uC694\uAD6C\uC0AC\uD56D"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 6960],
        rows: [
          labelValueRow("\uC608\uC0C1 \uB514\uC2A4\uD06C \uC0AC\uC6A9\uB7C9", "\uC57D 50MB (\uC571 \uCF54\uB4DC + DB + \uBC31\uC5C5)"),
          labelValueRow("\uBA54\uBAA8\uB9AC", "512MB \uC774\uD558"),
          labelValueRow("CPU", "\uCD5C\uC18C \uC0AC\uC591 (\uACBD\uB7C9 \uC6F9\uC571)"),
          labelValueRow("\uB124\uD2B8\uC6CC\uD06C", "\uC678\uBD80 \uC811\uC18D: \uD3EC\uD2B8 8501 \uAC1C\uBC29 \uD544\uC694"),
          labelValueRow("\uC678\uBD80 \uD1B5\uC2E0", "Google Sheets CSV \uB2E4\uC6B4\uB85C\uB4DC (\uD558\uB8E8 1\uD68C \uB3D9\uAE30\uD654)"),
          labelValueRow("\uBCF4\uC548", "\uB85C\uADF8\uC778 \uC2DC\uC2A4\uD15C \uB0B4\uC7A5 (ID/PW \uC778\uC99D)"),
        ]
      }),

      // ── 5. \uBC30\uD3EC \uD6C4 \uC6B4\uC601 ──
      heading("5. \uBC30\uD3EC \uD6C4 \uC6B4\uC601 \uBC29\uC2DD"),
      bodyText("\uBC30\uD3EC \uD6C4 \uC544\uB798\uC640 \uAC19\uC774 \uC790\uB3D9 \uC6B4\uC601\uB429\uB2C8\uB2E4:"),

      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "\uCEE8\uD14C\uC774\uB108 \uC2DC\uC791 \uC2DC Streamlit \uC6F9 \uC11C\uBC84 \uC790\uB3D9 \uAE30\uB3D9", font: "Arial", size: 20 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "NAS \uC7AC\uBD80\uD305 \uC2DC \uCEE8\uD14C\uC774\uB108 \uC790\uB3D9 \uC7AC\uC2DC\uC791 (restart: always)", font: "Arial", size: 20 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "\uB9E4\uC77C \uC0C8\uBCBD 3\uC2DC Google Sheets \u2192 SQLite \uC790\uB3D9 \uB3D9\uAE30\uD654", font: "Arial", size: 20 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "DB \uBC31\uC5C5 \uC790\uB3D9 \uC0DD\uC131 (7\uC77C \uBCF4\uAD00 \uD6C4 \uC790\uB3D9 \uC0AD\uC81C)", font: "Arial", size: 20 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 200 },
        children: [new TextRun({ text: "\uAD00\uB9AC\uC790 \uAC1C\uC785 \uD544\uC694 \uC5C6\uC74C (\uC571 \uC5C5\uB370\uC774\uD2B8 \uC2DC \uD30C\uC77C \uAD50\uCCB4 \uD6C4 \uCEE8\uD14C\uC774\uB108 \uC7AC\uC2DC\uC791\uB9CC \uD544\uC694)", font: "Arial", size: 20 })] }),

      // ── 6. \uC694\uCCAD \uC0AC\uD56D \uC694\uC57D ──
      heading("6. \uC694\uCCAD \uC0AC\uD56D \uC694\uC57D"),
      bodyText("\uC544\uB798 \uD56D\uBAA9\uC758 \uC124\uC815\uC744 \uBD80\uD0C1\uB4DC\uB9BD\uB2C8\uB2E4:"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [600, 6360, 2400],
        rows: [
          new TableRow({ children: [headerCell("No", 600), headerCell("\uC694\uCCAD \uC0AC\uD56D", 6360), headerCell("\uBE44\uACE0", 2400)] }),
          new TableRow({ children: [
            bodyCell("1", 600, { center: true }),
            bodyCell("NAS \uACF5\uC720 \uD3F4\uB354\uC5D0 /nas/uni-equipment/ \uD3F4\uB354 \uC0DD\uC131", 6360),
            bodyCell("\uD558\uC704 \uD3F4\uB354 \uD3EC\uD568", 2400)] }),
          new TableRow({ children: [
            bodyCell("2", 600, { center: true }),
            bodyCell("Docker \uCEE8\uD14C\uC774\uB108 \uC0DD\uC131 (uni-equipment, \uD3EC\uD2B8 8501)", 6360),
            bodyCell("python:3.11-slim", 2400)] }),
          new TableRow({ children: [
            bodyCell("3", 600, { center: true }),
            bodyCell("\uBCFC\uB968 \uB9C8\uC6B4\uD2B8: /nas/uni-equipment \u2192 /app", 6360),
            bodyCell("\uC77D\uAE30/\uC4F0\uAE30 \uAD8C\uD55C", 2400)] }),
          new TableRow({ children: [
            bodyCell("4", 600, { center: true }),
            bodyCell("\uD3EC\uD2B8 8501 \uC678\uBD80 \uC811\uADFC \uD5C8\uC6A9 (\uBC29\uD654\uBCBD/\uB77C\uC6B0\uD130)", 6360),
            bodyCell("\uB0B4\uBD80\uB9DD \uB610\uB294 VPN", 2400)] }),
          new TableRow({ children: [
            bodyCell("5", 600, { center: true }),
            bodyCell("\uCEE8\uD14C\uC774\uB108 \uC7AC\uC2DC\uC791 \uC815\uCC45: always", 6360),
            bodyCell("NAS \uC7AC\uBD80\uD305 \uB300\uBE44", 2400)] }),
          new TableRow({ children: [
            bodyCell("6", 600, { center: true }),
            bodyCell("\uD5A5\uD6C4 \uD3EC\uD2B8 8500, 8502, 8503 \uC608\uC57D (\uD604\uC7AC \uBBF8\uC0AC\uC6A9)", 6360),
            bodyCell("\uCD94\uD6C4 \uD655\uC7A5\uC6A9", 2400)] }),
        ]
      }),

      new Paragraph({ spacing: { before: 400 } }),

      // ── \uC694\uCCAD\uC790 \uC815\uBCF4 ──
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 6960],
        rows: [
          new TableRow({ children: [
            new TableCell({
              borders, width: { size: 9360, type: WidthType.DXA }, columnSpan: 2,
              shading: { fill: "F1F5F9", type: ShadingType.CLEAR }, margins: cellMargins,
              children: [new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "\uC694\uCCAD\uC790 \uC815\uBCF4", bold: true, font: "Arial", size: 20 })]
              })]
            })
          ] }),
          labelValueRow("\uC694\uCCAD\uC790", "(\uC774\uB984)"),
          labelValueRow("\uC5F0\uB77D\uCC98", "(\uC5F0\uB77D\uCC98)"),
          labelValueRow("\uBE44\uACE0", "\uCD08\uAE30 \uC138\uD305 \uC644\uB8CC \uD6C4 \uD30C\uC77C \uC5C5\uB85C\uB4DC \uBC0F \uCEE8\uD14C\uC774\uB108 \uC2DC\uC791 \uC548\uB0B4 \uBD80\uD0C1\uB4DC\uB9BD\uB2C8\uB2E4."),
        ]
      }),

      new Paragraph({ spacing: { before: 200 }, alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "Developed by smartbranding", font: "Arial", size: 16, color: "94A3B8", italics: true })] }),
    ]
  }]
});

const outPath = process.argv[2] || "NAS_Docker_요청서.docx";
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log("Created: " + outPath);
});
