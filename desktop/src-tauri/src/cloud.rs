use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::workspace::{ProviderModel, Settings};

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
    #[serde(skip_serializing_if = "Option::is_none")]
    pub references: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatCompletionRequest {
    pub messages: Vec<ChatMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub project_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub conversation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub scenes_excerpt: Option<String>,
    // Fields for LLM selection. External mode uses user-owned provider keys.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub llm_provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub use_personal_llm: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub use_autonomous_agent: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_runtime_version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublishRequest {
    pub title: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub scene_class: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duration: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublishResponse {
    pub id: String,
    pub status: String,
    #[serde(default)]
    pub message: String,
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
    #[serde(default)]
    pub agent_runtime_version: Option<String>,
    #[serde(default)]
    pub provider: Option<String>,
    #[serde(default)]
    pub billing_mode: Option<String>,
    #[serde(default)]
    pub request_id: Option<String>,
    #[serde(default)]
    pub agent_trace: Vec<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpenRouterKeyResponse {
    pub key: String,
    #[serde(default)]
    pub user_id: Option<String>,
}

fn content_to_text(value: &Value) -> String {
    match value {
        Value::String(text) => text.clone(),
        Value::Array(parts) => parts
            .iter()
            .filter_map(|part| {
                part.get("text")
                    .and_then(Value::as_str)
                    .or_else(|| part.get("content").and_then(Value::as_str))
            })
            .collect::<Vec<_>>()
            .join("\n"),
        _ => String::new(),
    }
}

pub async fn exchange_openrouter_code(
    code: &str,
    code_verifier: &str,
) -> Result<OpenRouterKeyResponse, String> {
    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let response = client
        .post("https://openrouter.ai/api/v1/auth/keys")
        .json(&json!({
            "code": code,
            "code_verifier": code_verifier,
            "code_challenge_method": "S256",
        }))
        .send()
        .await
        .map_err(|e| format!("OpenRouter key exchange failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!("OpenRouter key exchange HTTP {status}: {body}"));
    }

    response
        .json::<OpenRouterKeyResponse>()
        .await
        .map_err(|e| format!("parse OpenRouter key response: {e}"))
}

fn provider_api_key<'a>(settings: &'a Settings, provider: &str) -> Option<&'a str> {
    match provider {
        "openrouter" => settings.openrouter_api_key.as_deref(),
        "openai" => settings.openai_api_key.as_deref(),
        "groq" => settings.groq_api_key.as_deref(),
        "xai" => settings.xai_api_key.as_deref(),
        _ => None,
    }
    .map(str::trim)
    .filter(|key| !key.is_empty())
}

fn provider_base_url(provider: &str) -> Option<&'static str> {
    match provider {
        "openrouter" => Some("https://openrouter.ai/api/v1"),
        "openai" => Some("https://api.openai.com/v1"),
        "groq" => Some("https://api.groq.com/openai/v1"),
        "xai" => Some("https://api.x.ai/v1"),
        _ => None,
    }
}

fn default_model_for_provider(provider: &str) -> &'static str {
    match provider {
        "openrouter" => "openai/gpt-4o-mini",
        "openai" => "gpt-4o-mini",
        "groq" => "llama-3.1-8b-instant",
        "xai" => "grok-2-latest",
        _ => "gpt-4o-mini",
    }
}

fn normalize_model_for_provider(provider: &str, model: Option<String>) -> String {
    let selected = model.unwrap_or_else(|| default_model_for_provider(provider).to_string());
    if provider == "openrouter" {
        return selected;
    }
    if selected.starts_with("openai/") && provider == "openai" {
        return selected.trim_start_matches("openai/").to_string();
    }
    if selected.starts_with("groq/") && provider == "groq" {
        return selected.trim_start_matches("groq/").to_string();
    }
    if selected.starts_with("xai/") && provider == "xai" {
        return selected.trim_start_matches("xai/").to_string();
    }
    if selected.contains('/') {
        return default_model_for_provider(provider).to_string();
    }
    selected
}

pub async fn list_provider_models(
    settings: &Settings,
    provider: &str,
) -> Result<Vec<ProviderModel>, String> {
    let provider = provider.trim().to_lowercase();
    let base_url = provider_base_url(&provider)
        .ok_or_else(|| format!("Unsupported external AI provider: {provider}"))?;
    let api_key = provider_api_key(settings, &provider).ok_or_else(|| {
        format!(
            "No {} API key is stored on this computer. Add it in Settings > Providers.",
            provider
        )
    })?;

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let url = if provider == "openrouter" {
        format!("{base_url}/models?output_modalities=text&sort=most-popular")
    } else {
        format!("{base_url}/models")
    };
    let response = client
        .get(url)
        .bearer_auth(api_key)
        .header("HTTP-Referer", "https://matemium.app")
        .header("X-OpenRouter-Title", "Matemium")
        .send()
        .await
        .map_err(|e| format!("{provider} models request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!("{provider} models HTTP {status}: {body}"));
    }

    let payload = response
        .json::<Value>()
        .await
        .map_err(|e| format!("parse {provider} models response: {e}"))?;
    let data = payload
        .get("data")
        .and_then(Value::as_array)
        .ok_or_else(|| format!("{provider} models response did not include data[]"))?;

    let mut models = data
        .iter()
        .filter_map(|item| normalize_provider_model(&provider, item))
        .collect::<Vec<_>>();
    models.sort_by(|a, b| {
        score_provider_model(b)
            .cmp(&score_provider_model(a))
            .then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase()))
    });
    Ok(models)
}

fn normalize_provider_model(provider: &str, item: &Value) -> Option<ProviderModel> {
    let id = item.get("id")?.as_str()?.trim();
    if id.is_empty() || !looks_like_chat_model(provider, id, item) {
        return None;
    }
    let name = item
        .get("name")
        .and_then(Value::as_str)
        .or_else(|| item.get("label").and_then(Value::as_str))
        .unwrap_or(id)
        .to_string();
    let context_length = item
        .get("context_length")
        .or_else(|| item.get("contextWindow"))
        .or_else(|| item.get("context_window"))
        .or_else(|| item.get("ctx_len"))
        .and_then(Value::as_u64);
    let pricing_label = pricing_label(provider, id, item);
    let mut badges = Vec::new();
    if is_free_model(id, item) {
        badges.push("Free".to_string());
    }
    if context_length.unwrap_or(0) >= 100_000 {
        badges.push("Long context".to_string());
    }
    if item
        .get("supported_parameters")
        .and_then(Value::as_array)
        .map(|values| values.iter().any(|value| value.as_str() == Some("tools")))
        .unwrap_or(false)
    {
        badges.push("Tools".to_string());
    }
    if item
        .get("architecture")
        .and_then(|value| value.get("input_modalities"))
        .and_then(Value::as_array)
        .map(|values| values.iter().any(|value| value.as_str() == Some("image")))
        .unwrap_or(false)
    {
        badges.push("Vision".to_string());
    }

    Some(ProviderModel {
        id: id.to_string(),
        name,
        provider: provider.to_string(),
        context_length,
        pricing_label,
        badges,
    })
}

fn looks_like_chat_model(provider: &str, id: &str, item: &Value) -> bool {
    if item.get("active").and_then(Value::as_bool) == Some(false) {
        return false;
    }
    let lowered = id.to_lowercase();
    let excluded = [
        "embedding",
        "embed",
        "whisper",
        "tts",
        "dall-e",
        "image",
        "moderation",
        "audio",
        "transcribe",
        "vision-preview",
    ];
    if excluded.iter().any(|needle| lowered.contains(needle)) {
        return false;
    }
    if provider == "openrouter" {
        let output_modalities = item
            .get("architecture")
            .and_then(|value| value.get("output_modalities"))
            .and_then(Value::as_array);
        return output_modalities
            .map(|values| values.iter().any(|value| value.as_str() == Some("text")))
            .unwrap_or(true);
    }
    let included = [
        "gpt", "chatgpt", "o1", "o3", "o4", "llama", "mixtral", "gemma", "qwen", "deepseek",
        "compound", "grok", "kimi",
    ];
    included.iter().any(|needle| lowered.contains(needle))
}

fn pricing_label(provider: &str, id: &str, item: &Value) -> Option<String> {
    if is_free_model(id, item) {
        return Some("Free".to_string());
    }
    if provider != "openrouter" {
        return None;
    }
    let prompt_price = item
        .get("pricing")
        .and_then(|pricing| pricing.get("prompt"))
        .and_then(Value::as_str)
        .and_then(|value| value.parse::<f64>().ok())?;
    if prompt_price <= 0.0 {
        return Some("Free".to_string());
    }
    Some(format!("${:.2}/1M input", prompt_price * 1_000_000.0))
}

fn is_free_model(id: &str, item: &Value) -> bool {
    if id.ends_with(":free") || id == "openrouter/free" {
        return true;
    }
    let Some(pricing) = item.get("pricing") else {
        return false;
    };
    let prices = ["prompt", "completion", "request"]
        .iter()
        .filter_map(|key| pricing.get(*key))
        .collect::<Vec<_>>();
    !prices.is_empty()
        && prices.iter().all(|value| {
            value
                .as_str()
                .and_then(|raw| raw.parse::<f64>().ok())
                .or_else(|| value.as_f64())
                .unwrap_or(1.0)
                == 0.0
        })
}

fn score_provider_model(model: &ProviderModel) -> i32 {
    let id = model.id.to_lowercase();
    let mut score = 0;
    for needle in [
        "free", "gpt-4o", "claude", "deepseek", "llama", "grok", "qwen",
    ] {
        if id.contains(needle) {
            score += 10;
        }
    }
    if model.badges.iter().any(|badge| badge == "Free") {
        score += 20;
    }
    if model.badges.iter().any(|badge| badge == "Long context") {
        score += 5;
    }
    score
}

pub async fn external_provider_chat(
    settings: &Settings,
    mut request: ChatCompletionRequest,
) -> Result<ChatCompletionResponse, String> {
    let provider = settings
        .llm_provider
        .as_deref()
        .unwrap_or("openrouter")
        .trim()
        .to_lowercase();
    let api_key = provider_api_key(settings, &provider).ok_or_else(|| {
        format!(
            "No {} API key is stored on this computer. Add it in Settings > Providers.",
            provider
        )
    })?;
    let base_url = provider_base_url(&provider)
        .ok_or_else(|| format!("Unsupported external AI provider: {provider}"))?;
    let model = normalize_model_for_provider(
        &provider,
        request
            .model
            .take()
            .or_else(|| settings.external_llm_model.clone()),
    );

    let mut messages = Vec::new();
    if let Some(excerpt) = request
        .scenes_excerpt
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
    {
        messages.push(json!({
            "role": "system",
            "content": format!("Current Matemium project context:\n```python\n{excerpt}\n```"),
        }));
    }
    for message in request.messages {
        messages.push(json!({
            "role": message.role,
            "content": message.content,
        }));
    }

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(60))
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let response = client
        .post(format!("{base_url}/chat/completions"))
        .bearer_auth(api_key)
        .header("HTTP-Referer", "https://matemium.app")
        .header("X-OpenRouter-Title", "Matemium")
        .json(&json!({
            "model": model,
            "messages": messages,
        }))
        .send()
        .await
        .map_err(|e| format!("{provider} chat request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let retry_after = response
            .headers()
            .get("Retry-After")
            .and_then(|value| value.to_str().ok())
            .and_then(|value| value.parse::<u64>().ok());
        let body = response.text().await.unwrap_or_default();
        if provider == "openrouter" && model == "openrouter/free" && status.as_u16() == 429 {
            return Err(format!(
                "OPENROUTER_FREE_RATE_LIMITED:{}",
                retry_after.unwrap_or(0)
            ));
        }
        return Err(format!("{provider} chat HTTP {status}: {body}"));
    }

    let payload = response
        .json::<Value>()
        .await
        .map_err(|e| format!("parse {provider} chat response: {e}"))?;
    let choice = payload
        .get("choices")
        .and_then(Value::as_array)
        .and_then(|choices| choices.first())
        .ok_or_else(|| format!("{provider} response did not include choices[0]"))?;
    let message = choice
        .get("message")
        .ok_or_else(|| format!("{provider} response did not include choices[0].message"))?;
    let content = message
        .get("content")
        .map(content_to_text)
        .unwrap_or_default();

    Ok(ChatCompletionResponse {
        id: payload
            .get("id")
            .and_then(Value::as_str)
            .map(str::to_string)
            .unwrap_or_else(|| Uuid::new_v4().to_string()),
        message: ChatMessage {
            role: message
                .get("role")
                .and_then(Value::as_str)
                .unwrap_or("assistant")
                .to_string(),
            content,
            references: None,
        },
        code_edit: None,
        model: payload
            .get("model")
            .and_then(Value::as_str)
            .unwrap_or(&model)
            .to_string(),
        stub: false,
        agent_runtime_version: None,
        provider: Some(provider),
        billing_mode: Some("byo_external".to_string()),
        request_id: payload
            .get("id")
            .and_then(Value::as_str)
            .map(str::to_string)
            .or_else(|| Some(Uuid::new_v4().to_string())),
        agent_trace: Vec::new(),
    })
}

pub async fn login(settings: &Settings, email: &str, password: &str) -> Result<String, String> {
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
pub async fn login_with_session(settings: &Settings, access_token: &str) -> Result<String, String> {
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
        .json(&SessionBody {
            access_token: access_token.to_string(),
        })
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

pub async fn list_gallery(settings: &Settings, query: Option<&str>) -> Result<Value, String> {
    let base = settings.server_url.trim_end_matches('/');
    let mut url = format!("{base}/v1/gallery?status=published&limit=100");
    if let Some(q) = query {
        if !q.is_empty() {
            url.push_str(&format!("&search={}", urlencoding::encode(q)));
        }
    }

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(15))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("gallery request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "<empty body>".to_string());
        return Err(format!("gallery HTTP {status}: {body}"));
    }

    response
        .json::<Value>()
        .await
        .map_err(|e| format!("parse gallery response: {e}"))
}

pub async fn publish_to_gallery(
    settings: &Settings,
    request: PublishRequest,
) -> Result<PublishResponse, String> {
    let base = settings.server_url.trim_end_matches('/');
    let url = format!("{base}/v1/publish");

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    let mut req = client.post(url).json(&request);
    if let Some(token) = &settings.api_token {
        req = req.header("Authorization", format!("Bearer {token}"));
    }

    let response = req
        .send()
        .await
        .map_err(|e| format!("publish request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "<empty body>".to_string());
        return Err(format!("publish HTTP {status}: {body}"));
    }

    response
        .json::<PublishResponse>()
        .await
        .map_err(|e| format!("parse publish response: {e}"))
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
