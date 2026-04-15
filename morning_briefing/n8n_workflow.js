import { workflow, node, trigger, sticky, newCredential, ifElse, merge, expr } from '@n8n/workflow-sdk';

// ============================================
// 1. SCHEDULE TRIGGER - Weekdays 07:15 Berlin
// ============================================
const morningSchedule = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.3,
  config: {
    name: 'Weekday 07:15 Trigger',
    parameters: {
      rule: {
        interval: [{
          field: 'cronExpression',
          expression: '15 7 * * 1-5'
        }]
      }
    },
    position: [240, 300]
  },
  output: [{}]
});

// ============================================
// 2. RSS FEED READERS (with error tolerance)
// ============================================
const rssStartupVC = node({
  type: 'n8n-nodes-base.rssFeedRead',
  version: 1.2,
  config: {
    name: 'Fetch Startup & VC News',
    parameters: {
      url: 'https://news.google.com/rss/search?q=%22startup+funding%22+OR+%22venture+capital%22&hl=en&gl=US&ceid=US:en'
    },
    onError: 'continueRegularOutput',
    position: [540, 150]
  },
  output: [{ title: 'Startup raises $10M in Series A', link: 'https://example.com/news1', pubDate: 'Mon, 14 Apr 2026 10:00:00 GMT', contentSnippet: 'A startup has raised $10M in Series A funding from top VCs.' }]
});

const rssIoTEdgeAI = node({
  type: 'n8n-nodes-base.rssFeedRead',
  version: 1.2,
  config: {
    name: 'Fetch IoT & Edge AI News',
    parameters: {
      url: 'https://news.google.com/rss/search?q=%22IoT%22+OR+%22edge+AI%22&hl=en&gl=US&ceid=US:en'
    },
    onError: 'continueRegularOutput',
    position: [540, 450]
  },
  output: [{ title: 'Edge AI chip breakthrough announced', link: 'https://example.com/news2', pubDate: 'Mon, 14 Apr 2026 12:00:00 GMT', contentSnippet: 'New edge AI technology enables faster IoT processing.' }]
});

// ============================================
// 3. MERGE ALL NEWS (Append)
// ============================================
const mergeAllNews = merge({
  version: 3.2,
  config: {
    name: 'Combine All News Sources',
    parameters: { mode: 'append' },
    position: [840, 300]
  }
});

// ============================================
// 4. SCORE, DEDUP, FILTER TOP 5
// ============================================
const scoreAndFilter = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Score, Dedup & Select Top 5',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: 'const items = $input.all();\nconst now = new Date();\nconst oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);\n\nconst validItems = items.filter(item => {\n  if (!item.json.title || !item.json.link) return false;\n  const pubDate = new Date(item.json.pubDate || item.json.isoDate || 0);\n  return pubDate >= oneDayAgo;\n});\n\nconst seen = new Set();\nconst unique = validItems.filter(item => {\n  const key = (item.json.link || "").split("?")[0].toLowerCase();\n  if (seen.has(key)) return false;\n  seen.add(key);\n  return true;\n});\n\nconst scored = unique.map(item => {\n  let score = 0;\n  const text = ((item.json.title || "") + " " + (item.json.contentSnippet || item.json.content || "")).toLowerCase();\n  if (text.includes("startup")) score += 2;\n  if (text.includes("funding") || text.includes("raised")) score += 2;\n  if (text.includes("venture capital")) score += 2;\n  if (/series [a-d]/i.test(text)) score += 1;\n  if (text.includes("seed")) score += 1;\n  if (text.includes("investment")) score += 1;\n  if (text.includes("iot") || text.includes("internet of things")) score += 2;\n  if (text.includes("edge ai") || text.includes("edge computing")) score += 2;\n  if (text.includes("artificial intelligence")) score += 1;\n  if (text.includes("machine learning")) score += 1;\n  const desc = (item.json.contentSnippet || item.json.content || item.json.description || "").replace(/<[^>]*>/g, "").substring(0, 500);\n  return { json: { title: item.json.title, link: item.json.link, pubDate: item.json.pubDate || item.json.isoDate || "", description: desc, score: score, hasNews: true } };\n});\n\nscored.sort((a, b) => b.json.score - a.json.score);\nconst top5 = scored.slice(0, 5);\n\nif (top5.length === 0) {\n  return [{ json: { hasNews: false } }];\n}\nreturn top5;'
    },
    position: [1100, 300]
  },
  output: [{ title: 'Startup raises $10M', link: 'https://example.com/1', pubDate: '2026-04-14', description: 'Description text', score: 6, hasNews: true }]
});

// ============================================
// 5. CHECK IF NEWS EXISTS
// ============================================
const checkHasNews = ifElse({
  version: 2.3,
  config: {
    name: 'Has News?',
    parameters: {
      conditions: {
        conditions: [{
          leftValue: expr('{{ $json.hasNews }}'),
          operator: { type: 'boolean', operation: 'true' },
          rightValue: ''
        }]
      }
    },
    position: [1360, 300]
  }
});

// ============================================
// 6. PREPARE GEMINI PROMPT (aggregate items)
// ============================================
const preparePrompt = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Prepare Analysis Prompt',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: 'const items = $input.all();\nconst newsBlock = items.map((item, idx) =>\n  "--- HABER " + (idx + 1) + " ---\\n" +\n  "Baslik: " + item.json.title + "\\n" +\n  "Aciklama: " + item.json.description + "\\n" +\n  "Kaynak: " + item.json.link + "\\n" +\n  "Tarih: " + item.json.pubDate\n).join("\\n\\n");\n\nreturn [{ json: {\n  analysisPrompt: newsBlock,\n  newsData: items.map(i => i.json),\n  newsCount: items.length\n} }];'
    },
    position: [1620, 200]
  },
  output: [{ analysisPrompt: '--- HABER 1 ---\nBaslik: News\nAciklama: Desc\nKaynak: https://example.com\nTarih: 2026-04-14', newsData: [{ title: 'News', link: 'https://example.com', score: 6 }], newsCount: 1 }]
});

// ============================================
// 7. GOOGLE GEMINI STRATEGIC ANALYSIS
// ============================================
const geminiAnalysis = node({
  type: '@n8n/n8n-nodes-langchain.googleGemini',
  version: 1.1,
  config: {
    name: 'Generate Strategic Analysis',
    parameters: {
      resource: 'text',
      operation: 'message',
      modelId: { __rl: true, mode: 'list', value: 'models/gemini-2.0-flash' },
      messages: {
        values: [{
          content: expr(
            'Sen ust duzey bir stratejik is analisti ve teknoloji danismanisin. Asagidaki haberleri analiz et ve her biri icin Turkce, kisa ve keskin stratejik analiz uret.\n\n' +
            'ONEMLI: Sadece JSON formatinda yanit ver, baska hicbir sey ekleme.\n\n' +
            '{{ $json.analysisPrompt }}\n\n' +
            'Her haber icin su basliklarda analiz yap (her biri 1-2 cumle, somut ve aksiyon odakli, generic cumlelerden kacin):\n' +
            '- ne_oldu: Haberin net ozeti\n' +
            '- neden_onemli: Sektore ve piyasaya somut etkisi\n' +
            '- firsat: Bu haberden cikarilabilecek spesifik is firsati\n' +
            '- risk: Dikkat edilmesi gereken somut riskler\n' +
            '- aksiyon: Bugun atilabilecek somut bir adim\n\n' +
            'Ayrica tum haberleri butunsel olarak degerlendirip bugun_odak basliginda bugun odaklanilmasi gereken 3 maddelik kisa ve net bir liste olustur.\n\n' +
            'JSON formati:\n' +
            '{"analyses":[{"index":1,"ne_oldu":"...","neden_onemli":"...","firsat":"...","risk":"...","aksiyon":"..."}],"bugun_odak":"1. ...\\n2. ...\\n3. ..."}'
          ),
          role: 'user'
        }]
      },
      simplify: true,
      jsonOutput: true,
      options: {
        maxOutputTokens: 2048,
        temperature: 0.3
      }
    },
    credentials: { googlePalmApi: newCredential('Google Gemini') },
    onError: 'continueRegularOutput',
    position: [1880, 200]
  },
  output: [{ analyses: [{ index: 1, ne_oldu: 'Analiz', neden_onemli: 'Etki', firsat: 'Firsat', risk: 'Risk', aksiyon: 'Aksiyon' }], bugun_odak: '1. Odak 1\n2. Odak 2\n3. Odak 3' }]
});

// ============================================
// 8. COMPILE NEWSLETTER HTML
// ============================================
const compileNewsletter = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Compile Morning Newsletter',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: 'const geminiData = $input.first().json;\nconst newsItems = $("Prepare Analysis Prompt").first().json.newsData;\nconst today = new Date().toLocaleDateString("tr-TR", { weekday: "long", year: "numeric", month: "long", day: "numeric" });\n\nlet analyses = [];\nlet focusSummary = "";\ntry {\n  if (geminiData.analyses) {\n    analyses = geminiData.analyses;\n    focusSummary = geminiData.bugun_odak || "";\n  } else {\n    const raw = geminiData.text || geminiData.output || JSON.stringify(geminiData);\n    const match = raw.match(/\\{[\\s\\S]*\\}/);\n    if (match) {\n      const parsed = JSON.parse(match[0]);\n      analyses = parsed.analyses || [];\n      focusSummary = parsed.bugun_odak || "";\n    }\n  }\n} catch(e) {\n  focusSummary = "Analiz verisi islenemedi.";\n}\n\nlet html = \'<div style="font-family: Segoe UI, Arial, sans-serif; max-width: 680px; margin: 0 auto; background: #ffffff;">\';\nhtml += \'<div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 12px 12px 0 0;">\';\nhtml += \'<h1 style="color: #e94560; margin: 0; font-size: 24px;">Sabah Bulteni</h1>\';\nhtml += \'<p style="color: #a8a8b3; margin: 8px 0 0; font-size: 14px;">\' + today + \' | Startup & Tech Intelligence</p>\';\nhtml += \'</div>\';\nhtml += \'<div style="padding: 24px;">\';\n\nfor (let i = 0; i < newsItems.length; i++) {\n  const news = newsItems[i];\n  const a = analyses[i] || {};\n  html += \'<div style="margin-bottom: 24px; padding: 20px; background: #f8f9fa; border-left: 4px solid #e94560; border-radius: 0 8px 8px 0;">\';\n  html += \'<h2 style="margin: 0 0 8px; font-size: 16px; color: #1a1a2e;"><span style="color: #e94560; font-weight: bold;">#\' + (i+1) + \'</span> \' + (news.title || "") + \'</h2>\';\n  html += \'<p style="font-size: 12px; color: #666; margin: 0 0 12px;"><a href="\' + (news.link || "#") + \'" style="color: #4a90d9; text-decoration: none;">Kaynaga Git</a> | Skor: \' + (news.score || 0) + \' | \' + (news.pubDate || "") + \'</p>\';\n  if (a.ne_oldu) html += \'<div style="margin: 8px 0;"><strong style="color: #e94560;">Ne Oldu:</strong> \' + a.ne_oldu + \'</div>\';\n  if (a.neden_onemli) html += \'<div style="margin: 8px 0;"><strong style="color: #e94560;">Neden Onemli:</strong> \' + a.neden_onemli + \'</div>\';\n  if (a.firsat) html += \'<div style="margin: 8px 0;"><strong style="color: #2ecc71;">Firsat:</strong> \' + a.firsat + \'</div>\';\n  if (a.risk) html += \'<div style="margin: 8px 0;"><strong style="color: #e67e22;">Risk:</strong> \' + a.risk + \'</div>\';\n  if (a.aksiyon) html += \'<div style="margin: 8px 0;"><strong style="color: #3498db;">Aksiyon:</strong> \' + a.aksiyon + \'</div>\';\n  html += \'</div>\';\n}\n\nhtml += \'<div style="margin-top: 32px; padding: 20px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 8px;">\';\nhtml += \'<h2 style="color: #e94560; margin: 0 0 12px; font-size: 16px;">Bugun Odaklanman Gerekenler</h2>\';\nhtml += \'<div style="color: #e0e0e0; font-size: 14px; line-height: 1.8; white-space: pre-line;">\' + (focusSummary || "Bugun icin ozel bir odak noktasi belirlenmedi.") + \'</div>\';\nhtml += \'</div>\';\nhtml += \'</div>\';\nhtml += \'<div style="padding: 16px; text-align: center; color: #999; font-size: 11px; border-top: 1px solid #eee;">Bu bulten n8n ile otomatik olusturulmustur.</div>\';\nhtml += \'</div>\';\n\nreturn [{ json: { emailHtml: html, emailSubject: "Sabah Bulteni - " + today } }];'
    },
    position: [2140, 200]
  },
  output: [{ emailHtml: '<div>Newsletter</div>', emailSubject: 'Sabah Bulteni - 15 Nisan 2026' }]
});

// ============================================
// 9. SEND NEWSLETTER EMAIL
// ============================================
const sendNewsletter = node({
  type: 'n8n-nodes-base.gmail',
  version: 2.2,
  config: {
    name: 'Send Morning Newsletter',
    parameters: {
      resource: 'message',
      operation: 'send',
      sendTo: 'emre.terzioglu@icloud.com',
      subject: expr('{{ $json.emailSubject }}'),
      emailType: 'html',
      message: expr('{{ $json.emailHtml }}'),
      options: {
        appendAttribution: false,
        senderName: 'Morning Intelligence Bot'
      }
    },
    credentials: { gmailOAuth2: newCredential('Gmail') },
    position: [2400, 200]
  },
  output: [{ id: 'msg123', labelIds: ['SENT'], threadId: 'thread123' }]
});

// ============================================
// 10. SEND NO-NEWS EMAIL (False branch)
// ============================================
const sendNoNewsEmail = node({
  type: 'n8n-nodes-base.gmail',
  version: 2.2,
  config: {
    name: 'Send No News Alert',
    parameters: {
      resource: 'message',
      operation: 'send',
      sendTo: 'emre.terzioglu@icloud.com',
      subject: expr('Sabah Bulteni - {{ $now.toFormat("dd.MM.yyyy") }} | Haber Bulunamadi'),
      emailType: 'html',
      message: '<div style="font-family: Segoe UI, Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 40px; text-align: center;"><div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 12px;"><h1 style="color: #e94560; margin: 0 0 16px;">Sabah Bulteni</h1><p style="color: #a8a8b3; font-size: 16px; margin: 0;">Bugun izlenen konularda son 24 saatte yeni haber bulunamadi.</p><p style="color: #666; font-size: 14px; margin: 16px 0 0;">Takip edilen konular: Startup Funding, Venture Capital, IoT, Edge AI</p><p style="color: #4a90d9; font-size: 13px; margin: 16px 0 0;">Yarin tekrar kontrol edilecek.</p></div></div>',
      options: {
        appendAttribution: false,
        senderName: 'Morning Intelligence Bot'
      }
    },
    credentials: { gmailOAuth2: newCredential('Gmail') },
    position: [1620, 480]
  },
  output: [{ id: 'msg456', labelIds: ['SENT'], threadId: 'thread456' }]
});

// ============================================
// STICKY NOTES
// ============================================
const timezoneNote = sticky(
  '## Timezone Ayari\nn8n instance timezone ayarini Europe/Berlin olarak yapilandirin.\nSettings > General > Timezone > Europe/Berlin\n\nCron: Her hafta ici (Pzt-Cum) saat 07:15',
  [morningSchedule],
  { color: 4 }
);

const credentialNote = sticky(
  '## Credential Kurulumu\n1. Google Gemini: Google AI Studio API key gerekli (googlePalmApi)\n2. Gmail: OAuth2 credential ile yapilandirin (gmailOAuth2)\n\nHer iki credential da n8n Settings > Credentials sayfasindan olusturulmalidir.',
  [geminiAnalysis, sendNewsletter],
  { color: 2 }
);

// ============================================
// WORKFLOW COMPOSITION
// ============================================
export default workflow('news-morning-bulletin', 'Sabah Bulteni - Startup & Tech Intelligence')
  .add(morningSchedule)
  .to(rssStartupVC.to(mergeAllNews.input(0)))
  .add(morningSchedule)
  .to(rssIoTEdgeAI.to(mergeAllNews.input(1)))
  .add(mergeAllNews)
  .to(scoreAndFilter)
  .to(checkHasNews
    .onTrue(preparePrompt.to(geminiAnalysis.to(compileNewsletter.to(sendNewsletter))))
    .onFalse(sendNoNewsEmail)
  );
