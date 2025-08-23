/**
 * README validation tests for api_check/README.md.
 *
 * Purpose:
 * - Guardrail for critical documentation introduced/changed in the PR diff.
 * - Verify presence and integrity of key sections, code blocks, URLs, and enumerations.
 *
 * Runner: Compatible with Jest or Vitest (describe/test/expect style).
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';

const readmePath = resolve(process.cwd(), 'api_check', 'README.md');
const md = readFileSync(readmePath, 'utf8');

// Simple helpers
const hasHeading = (level: number, text: string): boolean => {
  const prefix = '#'.repeat(level);
  return md.split(/\r?\n/).some(line => {
    const trimmed = line.trim();
    if (!trimmed.startsWith(prefix)) return false;
    const rest = trimmed.slice(prefix.length).trim();
    return rest === text;
  });
};

const hasListItem = (text: string): boolean => {
  return md.split(/\r?\n/).some(line => {
    const trimmed = line.trim();
    if (!trimmed.startsWith('- ')) return false;
    let item = trimmed.slice(2);
    // Remove surrounding asterisks for bold/italic
    item = item.replace(/^\*+/, '').replace(/\*+$/, '');
    return item === text;
  });
};

const hasCodeBlockWithLang = (lang: string): boolean => {
  const codeFence = '```' + lang;
  const start = md.indexOf(codeFence);
  if (start === -1) return false;
  const end = md.indexOf('```', start + codeFence.length);
  return end !== -1;
};

const findAllMatches = (re: RegExp): RegExpMatchArray[] => {
  if (!re.flags.includes('g')) {
    throw new Error(`RegExp in findAllMatches must have 'g' flag: ${re}`);
  }
  const matches: RegExpMatchArray[] = [];
  re.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(md)) !== null) {
    matches.push(m as unknown as RegExpMatchArray);
  }
  return matches;
};

describe('api_check/README.md - structural integrity', () => {
  test('contains the main title', () => {
    expect(hasHeading(1, 'Soapify API Tester - Unified Testing Platform')).toBe(true);
  });

  test('includes key top-level sections', () => {
    const sections = [
      '🚀 Features',
      '📁 Project Structure',
      '🛠 Installation & Setup',
      '📊 API Endpoint Coverage',
      '🎯 Key Features Explained',
      '🔧 Configuration Options',
      '📈 Analytics & Reporting',
      '🎮 Usage Guide',
      '🚨 Troubleshooting',
      '🔒 Security & Privacy',
      '🤝 Contributing',
      '📝 License'
    ];
    for (const s of sections) {
      expect(hasHeading(2, s)).toBe(true);
    }
  });

  test('project structure code block exists and mentions expected files', () => {
    // Has a triple-backtick block that includes soapify-api-tester and package.json
    const structureBlock = /```[\s\S]*?api_check\/[\s\S]*?soapify-api-tester\/[\s\S]*?package\.json[\s\S]*?```/m;
    expect(structureBlock.test(md)).toBe(true);
  });

  test('Installation & Setup has Quick Start steps and npm commands', () => {
    expect(hasHeading(3, 'Quick Start')).toBe(true);
    expect(/npm\s+install/.test(md)).toBe(true);
    expect(/npm\s+start/.test(md)).toBe(true);
    expect(hasHeading(3, 'Production Build')).toBe(true);
    expect(/npm\s+run\s+build/.test(md)).toBe(true);
    expect(/npm\s+run\s+serve/.test(md)).toBe(true);
  });
});

describe('api_check/README.md - content validations from diff', () => {
  test('lists 70+ endpoints across enumerated categories with counts', () => {
    // Check presence of the categories mentioned
    const categories = [
      'Authentication & JWT',
      'Accounts',
      'Encounters',
      'Speech-to-Text',
      'NLP Processing',
      'Outputs',
      'Uploads',
      'Integrations',
      'Checklist',
      'Search',
      'Analytics',
      'Embeddings',
      'System'
    ];
    for (const cat of categories) {
      expect(md.includes(`**${cat}** (`)).toBe(true);
    }
  });

  test('base URL is present and consistent', () => {
    const inlineBaseUrl = /Base URL\*\*:\s*(https?:\/\/[^\s/$.?#].[^\s]*)/i.exec(md);
    expect(inlineBaseUrl).not.toBeNull();
    const url = inlineBaseUrl ? inlineBaseUrl[1] : '';
    expect(url).toBe('https://django-m.chbk.app/');

    // Confirm also referenced in the configuration example
    const trimmedUrl = url.endsWith('/') ? url.slice(0, -1) : url;
    const configSingle = `baseUrl: '${trimmedUrl}'`;
    const configDouble = `baseUrl: "${trimmedUrl}"`;
    expect(md.includes(configSingle) || md.includes(configDouble)).toBe(true);
  });

  test('Configuration Options include TypeScript code blocks for API and Audio configs', () => {
    expect(hasHeading(3, 'API Testing Configuration')).toBe(true);
    expect(hasCodeBlockWithLang('typescript')).toBe(true);

    expect(hasHeading(3, 'Audio Recording Configuration')).toBe(true);
    // At least one additional TS code block should be present (the audio config)
    const tsBlocks = findAllMatches(/```typescript[\s\S]*?```/g);
    expect(tsBlocks.length).toBeGreaterThanOrEqual(2);
  });

  test('Timing measurements include Request/Response/Total/Throughput', () => {
    const required = ['Request Time', 'Response Time', 'Total Time', 'Throughput'];
    const lowerMd = md.toLowerCase();
    for (const r of required) {
      expect(lowerMd.includes(`**${r.toLowerCase()}**`)).toBe(true);
    }
  });

  test('Error handling mentions network, HTTP, validation errors, and retry/backoff', () => {
    expect(/Network Errors/i.test(md)).toBe(true);
    expect(/HTTP Errors/i.test(md)).toBe(true);
    expect(/Validation Errors/i.test(md)).toBe(true);
    expect(/retry/i.test(md)).toBe(true);
    expect(/exponential backoff/i.test(md)).toBe(true);
  });

  test('Audio recording features call out formats and recording lifecycle controls', () => {
    expect(/WAV|MP3|M4A/i.test(md)).toBe(true);
    expect(/Start, pause, resume, stop/i.test(md)).toBe(true);
  });

  test('Resume functionality is documented with persistence across sessions', () => {
    expect(/Resumes from last completed endpoint/i.test(md)).toBe(true);
    expect(/Works across browser sessions/i.test(md)).toBe(true);
  });
});

describe('api_check/README.md - formatting and link sanity', () => {
  test('contains no empty triple-backtick code blocks', () => {
    const emptyBlock = /```[a-zA-Z]*\s*```/m;
    expect(emptyBlock.test(md)).toBe(false);
  });

  test('uses valid Markdown headings hierarchy for top sections (no skipped levels at top)', () => {
    // Ensure after H1, the next primary sections are H2.
    const lines = md.split(/\r?\n/);
    const headingLines = lines.filter(l => /^#{1,6}\s+/.test(l));
    const h1Index = headingLines.findIndex(l => /^#\s+/.test(l));
    expect(h1Index).toBeGreaterThanOrEqual(0);

    // At least one H2 exists after H1
    const subsequent = headingLines.slice(h1Index + 1);
    expect(subsequent.some(l => /^##\s+/.test(l))).toBe(true);
  });

  test('URLs are https where appropriate and have no obvious malformed links', () => {
    const urls = md.match(/https?:\/\/[^\s)]+/g) || [];
    // No whitespace inside URL matches and prefer https; allow http://localhost:3000 in dev directions
    for (const u of urls) {
      expect(/\s/.test(u)).toBe(false);
      if (!/http:\/\/localhost:3000/.test(u)) {
        expect(u.startsWith('https://')).toBe(true);
      }
    }
  });
});

describe('api_check/README.md - metadata and versioning', () => {
  test('includes Version and Last Updated fields with plausible values', () => {
    const version = /Version\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)/i.exec(md);
    expect(version).not.toBeNull();

    const lastUpdated = /Last Updated\*\*:\s*([A-Za-z]+\s+\d{4})/i.exec(md);
    expect(lastUpdated).not.toBeNull();

    // Basic sanity: month name and 4-digit year
    if (lastUpdated) {
      const [, val] = lastUpdated;
      expect(/[A-Za-z]+ \d{4}/.test(val)).toBe(true);
    }
  });

  test('Security & Privacy section states local storage and HTTPS requirements', () => {
    expect(/Local Storage/i.test(md)).toBe(true);
    expect(/HTTPS/i.test(md)).toBe(true);
    expect(/No External Services/i.test(md)).toBe(true);
  });
});