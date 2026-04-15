import {
  workflow,
  node,
  trigger,
  sticky,
  merge,
  languageModel,
  newCredential,
  placeholder,
  expr,
} from "@n8n/workflow-sdk";

// 1. Schedule Trigger — every day at 7:00 AM
const scheduleTrigger = trigger({
  type: "n8n-nodes-base.scheduleTrigger",
  version: 1.3,
  config: {
    name: "Every Morning at 7 AM",
    parameters: {
      rule: {
        interval: [
          {
            field: "days",
            daysInterval: 1,
            triggerAtHour: 7,
            triggerAtMinute: 0,
          },
        ],
      },
    },
    position: [240, 300],
  },
  output: [{}],
});

// 2a. Fetch top news via RSS (Google News)
const fetchNews = node({
  type: "n8n-nodes-base.rssFeedRead",
  version: 1.2,
  config: {
    name: "Fetch Top News",
    parameters: {
      url: "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    },
    position: [520, 100],
  },
  output: [
    {
      title: "Breaking News Headline",
      link: "https://news.google.com/1",
      contentSnippet: "Summary of news article...",
    },
    {
      title: "World News Update",
      link: "https://news.google.com/2",
      contentSnippet: "Another summary...",
    },
  ],
});

// 2b. Fetch top Hacker News stories
const fetchHackerNews = node({
  type: "n8n-nodes-base.hackerNews",
  version: 1,
  config: {
    name: "Fetch Tech News",
    parameters: {
      resource: "all",
      operation: "getAll",
      limit: 5,
      additionalFields: {
        tags: ["front_page"],
      },
    },
    position: [520, 300],
  },
  output: [
    {
      title: "Show HN: Cool project",
      url: "https://example.com",
      author: "user1",
      num_comments: 42,
    },
    {
      title: "AI breakthrough paper",
      url: "https://arxiv.org/1",
      author: "user2",
      num_comments: 100,
    },
  ],
});

// 2c. Fetch current weather
const fetchWeather = node({
  type: "n8n-nodes-base.openWeatherMap",
  version: 1,
  config: {
    name: "Fetch Weather",
    parameters: {
      operation: "currentWeather",
      format: "metric",
      locationSelection: "cityName",
      cityName: placeholder("Your city name (e.g. New York)"),
      language: "en",
    },
    credentials: { openWeatherMapApi: newCredential("OpenWeatherMap") },
    position: [520, 500],
  },
  output: [
    {
      name: "New York",
      main: { temp: 18, feels_like: 16, humidity: 65 },
      weather: [{ description: "partly cloudy" }],
      wind: { speed: 5.2 },
    },
  ],
});

// 3. Merge all three data sources (append mode)
const mergeData = merge({
  version: 3.2,
  config: {
    name: "Combine All Data",
    parameters: { mode: "append", numberInputs: 3 },
    position: [800, 300],
  },
});

// 4. Code node — aggregate all items into a single prompt context
const formatBriefContext = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    name: "Format Brief Context",
    parameters: {
      mode: "runOnceForAllItems",
      language: "javaScript",
      jsCode: `const items = $input.all();

let newsSection = "## Top News Headlines\\n";
let techSection = "## Tech / Hacker News\\n";
let weatherSection = "## Weather\\n";

for (const item of items) {
  const d = item.json;
  if (d.main && d.weather) {
    // Weather item
    weatherSection += \`City: \${d.name}\\n\`;
    weatherSection += \`Temperature: \${d.main.temp}°C (feels like \${d.main.feels_like}°C)\\n\`;
    weatherSection += \`Conditions: \${d.weather[0]?.description}\\n\`;
    weatherSection += \`Humidity: \${d.main.humidity}%, Wind: \${d.wind?.speed} m/s\\n\\n\`;
  } else if (d.num_comments !== undefined) {
    // Hacker News item
    techSection += \`- \${d.title} (by \${d.author}, \${d.num_comments} comments)\\n  \${d.url || ''}\\n\`;
  } else if (d.title) {
    // RSS news item
    newsSection += \`- \${d.title}\\n  \${d.link || ''}\\n\`;
  }
}

const briefContext = weatherSection + "\\n" + newsSection + "\\n" + techSection;
return [{ json: { briefContext } }];`,
    },
    position: [1060, 300],
  },
  output: [
    {
      briefContext:
        "## Weather\nCity: New York\nTemp: 18°C\n\n## Top News\n- Breaking headline\n\n## Tech\n- Show HN: Cool project",
    },
  ],
});

// 5. OpenAI Chat Model (subnode for the AI agent)
const openAiModel = languageModel({
  type: "@n8n/n8n-nodes-langchain.lmChatOpenAi",
  version: 1.3,
  config: {
    name: "OpenAI GPT",
    parameters: {
      model: { __rl: true, mode: "list", value: "gpt-4o-mini" },
      options: {
        temperature: 0.7,
      },
    },
    credentials: { openAiApi: newCredential("OpenAI") },
    position: [1320, 500],
  },
});

// 6. AI Agent — generate the morning brief
const aiAgent = node({
  type: "@n8n/n8n-nodes-langchain.agent",
  version: 3.1,
  config: {
    name: "Generate Morning Brief",
    parameters: {
      promptType: "define",
      text: expr(
        "Create my morning brief from this data:\\n\\n{{ $json.briefContext }}"
      ),
      options: {
        systemMessage:
          "You are a personal morning briefing assistant. Your job is to create a concise, well-formatted daily morning brief in HTML format. Structure it with clear sections: Weather Overview, Top News Headlines (pick the 5 most important), and Tech News Highlights. Use a friendly, professional tone. Add a brief motivational quote at the end. Keep the total brief scannable — no more than 500 words. Format with HTML tags (h2, ul, li, p, strong) for email readability.",
      },
    },
    subnodes: { model: openAiModel },
    position: [1320, 300],
  },
  output: [
    { output: "<h2>Good Morning!</h2><p>Here is your daily brief...</p>" },
  ],
});

// 7. Send via Gmail
const sendEmail = node({
  type: "n8n-nodes-base.gmail",
  version: 2.2,
  config: {
    name: "Send Morning Brief Email",
    parameters: {
      resource: "message",
      operation: "send",
      sendTo: placeholder("Your email address (e.g. you@gmail.com)"),
      subject: expr(
        'Your Morning Brief - {{ $now.toFormat("MMMM d, yyyy") }}'
      ),
      emailType: "html",
      message: expr("{{ $json.output }}"),
      options: {
        appendAttribution: false,
        senderName: "Morning Brief AI",
      },
    },
    credentials: { gmailOAuth2: newCredential("Gmail") },
    position: [1580, 300],
  },
  output: [{ id: "msg123", threadId: "thread456", labelIds: ["SENT"] }],
});

// Sticky notes for user guidance
const setupNote = sticky(
  "## Setup Instructions\n1. Add your **OpenWeatherMap** API credentials\n2. Add your **OpenAI** API key\n3. Add your **Gmail** OAuth2 credentials\n4. Set your city name in the Weather node\n5. Set your email address in the Gmail node\n6. Activate the workflow!",
  [scheduleTrigger],
  { color: 4 }
);

const designNote = sticky(
  "## How It Works\nEvery morning at 7 AM:\n1. Fetches top news from Google News RSS\n2. Fetches top Hacker News stories\n3. Gets current weather for your city\n4. AI summarizes everything into a brief\n5. Sends it to your inbox as a formatted email",
  [sendEmail],
  { color: 2 }
);

// Compose workflow — parallel branches into merge, then AI summarization + email
export default workflow("morning-brief", "AI Morning Brief")
  .add(scheduleTrigger)
  .to(fetchNews.to(mergeData.input(0)))
  .add(scheduleTrigger)
  .to(fetchHackerNews.to(mergeData.input(1)))
  .add(scheduleTrigger)
  .to(fetchWeather.to(mergeData.input(2)))
  .add(mergeData)
  .to(formatBriefContext)
  .to(aiAgent)
  .to(sendEmail);
