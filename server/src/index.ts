import express from 'express';
import cors from 'cors';

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

app.get('/api/hello', (req, res) => {
  res.json({ message: 'Story Engine BFF Server is running!' });
});

// --- 1. Story Bootstrap ---
// Maps to: Prompt 1 (02_panel_generation.md)
app.post('/api/story/bootstrap', (req, res) => {
  // Expected body: { storyTitle, divergence, genre }
  
  res.json({
    panels: [
      { caption: "The sun set on a world forever changed.", scene: "city" },
      { caption: "In the quiet that followed, a choice had to be made.", scene: "room" }
    ],
    checkpoint: {
      moment: "The path diverges in the fading light.",
      choices: [
        { text: "Leave before dawn.", genre: "Bold", hint: "Escape the impending danger." },
        { text: "Wait for the others.", genre: "Hopeful", hint: "Trust that help is coming." },
        { text: "Set a trap.", genre: "Strategic", hint: "Prepare for a confrontation." }
      ]
    }
  });
});

// --- 2A. Panel Continuation (Preset Choice) ---
// Maps to: Prompt 2A (02_panel_generation.md)
app.post('/api/story/continue', (req, res) => {
  const { storySoFar, choiceText, choiceGenre, panelsRemaining } = req.body;
  
  const response: any = {
    panels: [
      { caption: "Taking that step felt heavier than expected.", scene: "road" },
      { caption: "But momentum carried them forward into the unknown.", scene: "forest" }
    ],
    checkpoint: null
  };

  // If PANELS_REMAINING is 2 or fewer, set "checkpoint" to null.
  if (panelsRemaining > 2) {
    response.checkpoint = {
      moment: "A sudden noise breaks the silence.",
      choices: [
        { text: "Hide in the shadows.", genre: "Grounded", hint: "Avoid detection at all costs." },
        { text: "Call out to the noise.", genre: "Bold", hint: "Confront whatever is out there." }
      ]
    };
  }

  res.json(response);
});

// --- 2B. Dynamic Checkpoint ---
// Maps to: Prompt 2B (03_checkpoints.md)
app.post('/api/story/checkpoint', (req, res) => {
  // Expected body: { lastPanelCaption, storySoFar, panelsRemaining }
  
  res.json({
    checkpoint: {
      moment: "The situation shifts dramatically.",
      choices: [
        { text: "Adapt to the new reality.", genre: "Strategic", hint: "Change plans immediately." },
        { text: "Hold onto the original goal.", genre: "Hopeful", hint: "Stay true to the mission." },
        { text: "Abandon everything.", genre: "Free", hint: "Walk away from it all." }
      ]
    }
  });
});

// --- 3-PRE. User Input Validation ---
// Maps to: Prompt 3-PRE (04_user_narration.md)
app.post('/api/story/validate', (req, res) => {
  const { userInput, storyContext } = req.body;
  
  // Basic mock validation: ensure input is not empty
  const isUsable = userInput && userInput.trim().length > 0;
  
  res.json({
    usable: !!isUsable,
    reason: isUsable ? "" : "Input cannot be empty.",
    sanitised: isUsable ? userInput.trim() : ""
  });
});

// --- 3. User Narration Injection ---
// Maps to: Prompt 3 (04_user_narration.md)
app.post('/api/story/narration', (req, res) => {
  const { storySoFar, userInput, panelsRemaining } = req.body;
  
  const response: any = {
    panels: [
      { caption: "The world seemed to bend to this new intention.", scene: "night" },
      { caption: "Things would never be the same after this.", scene: "market" }
    ],
    absorbed: `✦ Your idea: "${userInput || 'something unexpected'}" was woven into the story.`,
    checkpoint: null
  };

  if (panelsRemaining > 2) {
    response.checkpoint = {
      moment: "The aftermath leaves a lingering question.",
      choices: [
        { text: "Embrace the consequences.", genre: "Dark", hint: "Accept what has been done." },
        { text: "Try to fix it.", genre: "Hopeful", hint: "Seek redemption." }
      ]
    };
  }

  res.json(response);
});

// --- 4A, 4B, 4C. AI Endings ---
// Maps to: Prompts 4A, 4B, 4C (05_ai_endings.md)
app.post('/api/story/ending', (req, res) => {
  // Expected body: { triggerType, storySoFar, lastPanelCaption, genre, userEndingInput }
  // triggerType can be "user_choice", "panel_limit", or "user_ending"
  
  res.json({
    final_panel: {
      caption: "The stillness was absolute, freezing the world in place.",
      scene: "dawn"
    },
    rest: "The door was still open. She hadn't decided yet whether that was an invitation or a warning."
  });
});

// --- Helper: Update Summary ---
// Maps to: Helper prompt (06_helpers_and_variables.md)
app.post('/api/story/summary', (req, res) => {
  const { storySoFar, newPanel1, newPanel2, choiceMade } = req.body;
  
  // Mocking the updated summary behaviour
  const addition = choiceMade ? ` → ${choiceMade}` : " → events continued";
  const newSummary = storySoFar ? `${storySoFar}${addition}` : `Started new journey${addition}`;
  
  res.json({ summary: newSummary });
});

app.listen(port, () => {
  console.log(`BFF Server running on http://localhost:${port}`);
});
