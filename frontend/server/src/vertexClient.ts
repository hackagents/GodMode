import { GoogleAuth } from 'google-auth-library';
import dotenv from 'dotenv';

dotenv.config();

// Standard Google Cloud config
const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || 'YOUR_PROJECT_ID';
const LOCATION = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';
// The ID of your deployed Reasoning Engine (found in Vertex AI Console)
const REASONING_ENGINE_ID = process.env.VERTEX_REASONING_ENGINE_ID || 'YOUR_ENGINE_ID';

// Initialize Google Auth (uses Application Default Credentials)
const auth = new GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/cloud-platform']
});

/**
 * Queries a deployed Vertex AI Reasoning Engine (ADK Agent).
 * @param input The prompt or input to send to the agent.
 * @returns The agent's response.
 */
export async function queryVertexAgent(input: string): Promise<any> {
  try {
    // 1. Get an authenticated client and a valid access token
    const client = await auth.getClient();
    const accessToken = await client.getAccessToken();

    if (!accessToken.token) {
      throw new Error("Failed to retrieve Google Cloud access token.");
    }

    // 2. Construct the specific REST endpoint for your deployed agent
    const endpointUrl = `https://${LOCATION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/reasoningEngines/${REASONING_ENGINE_ID}:query`;

    // 3. Make the API call to the agent
    const response = await fetch(endpointUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input: {
          input: input
        }
      })
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`Vertex AI API Error: ${response.status} - ${errorBody}`);
    }

    const data = await response.json();
    
    // The ADK agent response structure will depend on your Python code return values.
    // By default, Reasoning Engine returns { "output": ... } or { "response": ... }
    return data;

  } catch (error) {
    console.error("Error communicating with Vertex Agent:", error);
    throw error;
  }
}
