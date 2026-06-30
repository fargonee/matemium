use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::workspace::Settings;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TokenRequest {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenResponse {
    pub access_token: String,
    #[serde(default = "default_token_type")]
    pub token_type: String,
    #[serde(default)]
    pub expires_in: u64,
}

fn default_token_type() -> String {
    "bearer".to_string()
}

pub fn extract_access_token(response: &TokenResponse) -> String {
    response.access_token.clone()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatCompletionRequest {
    pub messages: Vec<ChatMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub project_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub scenes_excerpt: Option<String>,
    // New fields for LLM selection (BYO personal keys or platform pool)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub llm_provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub use_personal_llm: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeEdit {
    pub description: String,
    #[serde(default)]
    pub search: Option<String>,
    #[serde(default)]
    pub replace: Option<String>,
    #[serde(default)]
    pub full_file: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatCompletionResponse {
    pub id: String,
    pub message: ChatMessage,
    #[serde(default)]
    pub code_edit: Option<CodeEdit>,
    pub model: String,
    #[serde(default)]
    pub stub: bool,
}

pub async fn login(
    settings: &Settings,
    email: &str,
    password: &str,
) -> Result<String, String> {
    let base = settings.server_url.trim_end_matches('/');
    let url = format!("{base}/v1/auth/token");

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    let body = TokenRequest {
        email: email.to_string(),
        password: password.to_string(),
    };

    let response = client
        .post(url)
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("auth request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "<empty body>".to_string());
        return Err(format!("auth HTTP {status}: {body}"));
    }

    let token = response
        .json::<TokenResponse>()
        .await
        .map_err(|e| format!("parse auth response: {e}"))?;

    Ok(extract_access_token(&token))
}

// For production Supabase Google sign-in: exchange web access_token
pub async fn login_with_session(
    settings: &Settings,
    access_token: &str,
) -> Result<String, String> {
    let base = settings.server_url.trim_end_matches('/');
    let url = format!("{base}/v1/auth/session");

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    #[derive(Serialize)]
    struct SessionBody {
        access_token: String,
    }

    let response = client
        .post(url)
        .json(&SessionBody { access_token: access_token.to_string() })
        .send()
        .await
        .map_err(|e| format!("session auth failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!("session HTTP {status}: {body}"));
    }

    let token = response
        .json::<TokenResponse>()
        .await
        .map_err(|e| format!("parse session response: {e}"))?;

    Ok(extract_access_token(&token))
}

pub async fn chat(
    settings: &Settings,
    request: ChatCompletionRequest,
) -> Result<ChatCompletionResponse, String> {
    let base = settings.server_url.trim_end_matches('/');
    let url = format!("{base}/v1/chat/completions");

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(60))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    let mut req = client.post(url).json(&request);
    if let Some(token) = &settings.api_token {
        req = req.header("Authorization", format!("Bearer {token}"));
    }

    let response = req
        .send()
        .await
        .map_err(|e| format!("chat request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "<empty body>".to_string());
        return Err(format!("chat HTTP {status}: {body}"));
    }

    response
        .json::<ChatCompletionResponse>()
        .await
        .map_err(|e| format!("parse chat response: {e}"))
}

pub async fn chat_raw(
    settings: &Settings,
    request: ChatCompletionRequest,
) -> Result<Value, String> {
    let response = chat(settings, request).await?;
    serde_json::to_value(response).map_err(|e| format!("serialize chat response: {e}"))
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioSpeechRequest {
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub voice: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tts_provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub use_personal_llm: Option<bool>,
}

pub async fn generate_audio(
    settings: &Settings,
    request: AudioSpeechRequest,
) -> Result<Vec<u8>, String> {
    let base = settings.server_url.trim_end_matches('/');
    let url = format!("{base}/v1/audio/speech");

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(120))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    let mut req = client.post(url).json(&request);
    if let Some(token) = &settings.api_token {
        req = req.header("Authorization", format!("Bearer {token}"));
    }

    let response = req
        .send()
        .await
        .map_err(|e| format!("audio request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "<empty body>".to_string());
        return Err(format!("audio HTTP {status}: {body}"));
    }

    let bytes = response
        .bytes()
        .await
        .map_err(|e| format!("read audio bytes: {e}"))?;
    Ok(bytes.to_vec())
}

pub async fn get_profile(settings: &Settings) -> Result<Value, String> {
    let base = settings.server_url.trim_end_matches('/');
    let url = format!("{base}/v1/me");

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    let mut req = client.get(url);
    if let Some(token) = &settings.api_token {
        req = req.header("Authorization", format!("Bearer {token}"));
    }

    let response = req
        .send()
        .await
        .map_err(|e| format!("profile request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "<empty body>".to_string());
        return Err(format!("profile HTTP {status}: {body}"));
    }

    response
        .json::<Value>()
        .await
        .map_err(|e| format!("parse profile response: {e}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extract_access_token_returns_bearer_value() {
        let response = TokenResponse {
            access_token: "dev.user.token".to_string(),
            token_type: "bearer".to_string(),
            expires_in: 604800,
        };
        assert_eq!(extract_access_token(&response), "dev.user.token");
    }
}