import { GoogleAuth } from 'google-auth-library';
import dotenv from 'dotenv';

dotenv.config();

const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || 'YOUR_PROJECT_ID';
const LOCATION = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

// Initialize Google Auth (uses Application Default Credentials)
const auth = new GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/cloud-platform']
});

/**
 * Generates an image using Google's Imagen model via Vertex AI.
 * @param prompt The descriptive prompt for the image.
 * @returns A base64 encoded string of the generated image.
 */
export async function generateImage(prompt: string): Promise<string | null> {
  try {
    const client = await auth.getClient();
    const accessToken = await client.getAccessToken();

    if (!accessToken.token) {
      throw new Error("Failed to retrieve Google Cloud access token.");
    }

    // Imagen uses the publishers/google/models path and the :predict endpoint
    const endpointUrl = `https://aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/imagen-4.0-fast-generate-001:predict`;

    const requestBody = {
      instances: [
        {
          prompt: prompt
        }
      ],
      parameters: {
        sampleCount: 1,
        aspectRatio: "16:9"
      }
    };

    const response = await fetch(endpointUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`Vertex AI API Error: ${response.status} - ${errorBody}`);
    }

    const data = await response.json();
    // The response contains an array of predictions, each with a bytesBase64Encoded field
    const predictions = data.predictions;
    if (predictions && predictions.length > 0) {
       return predictions[0].bytesBase64Encoded || null;
    }

    return null;
  } catch (error) {
    console.error("Error generating image with Imagen:", error);
    throw error;
  }
}
