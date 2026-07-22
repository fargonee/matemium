use std::collections::HashSet;

use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::State;

use crate::assets::DownloadableAssetSpec;
use crate::state::AppState;

const HF_API_BASE: &str = "https://huggingface.co/api";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LocalModelCatalogEntry {
    pub repo_id: String,
    pub display_name: String,
    pub family: String,
    pub file_name: String,
    pub download_url: String,
    pub size_bytes: u64,
    pub expected_sha256: Option<String>,
    pub context_length: Option<u64>,
    pub parameter_size: Option<String>,
    pub quantization: Option<String>,
    pub license: Option<String>,
    pub tags: Vec<String>,
    pub asset_id: String,
    pub install_path: String,
    pub source_repo_url: String,
    pub installed: bool,
}

impl LocalModelCatalogEntry {
    pub fn to_downloadable_asset(&self) -> DownloadableAssetSpec {
        DownloadableAssetSpec {
            id: self.asset_id.clone(),
            display_name: Some(self.display_name.clone()),
            asset_type: Some("local_model".to_string()),
            source_url: self.download_url.clone(),
            expected_sha256: self.expected_sha256.clone(),
            size: self.size_bytes,
            extract: false,
            extract_format: "none".to_string(),
            install_path: self.install_path.clone(),
        }
    }
}

async fn http_client() -> Result<Client, String> {
    Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())
}

fn model_page_url(repo_id: &str) -> String {
    format!("https://huggingface.co/{repo_id}")
}

fn asset_id_for(repo_id: &str, file_name: &str) -> String {
    let base = format!("hf-{}-{}", repo_id.replace('/', "-"), file_name);
    base.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' || c == '_' {
                c
            } else {
                '-'
            }
        })
        .collect()
}

fn install_path_for(repo_id: &str, file_name: &str) -> String {
    format!("models/hf/{}/{}", repo_id.replace('/', "__"), file_name)
}

fn family_label(repo_id: &str) -> String {
    repo_id
        .split('/')
        .last()
        .unwrap_or(repo_id)
        .replace('-', " ")
}

fn search_score(file_name: &str) -> i32 {
    let lower = file_name.to_lowercase();
    let mut score = 0;
    if lower.ends_with(".gguf") {
        score += 100;
    }
    if lower.contains("q4_k_m") {
        score += 40;
    } else if lower.contains("q4") {
        score += 30;
    }
    if lower.contains("q5") {
        score += 20;
    }
    if lower.contains("q6") {
        score += 15;
    }
    if lower.contains("q8") {
        score += 10;
    }
    if lower.contains("mmproj") || lower.contains("imatrix") || lower.contains("embedding") {
        score -= 200;
    }
    score - (lower.len() as i32 / 10)
}

fn vec_string_field(value: &Value, key: &str) -> Vec<String> {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_str().map(ToString::to_string))
                .collect()
        })
        .unwrap_or_default()
}

fn extract_license(repo_info: &Value) -> Option<String> {
    repo_info
        .get("cardData")
        .and_then(|value| value.get("license"))
        .and_then(Value::as_str)
        .map(ToString::to_string)
        .or_else(|| {
            repo_info
                .get("license")
                .and_then(Value::as_str)
                .map(ToString::to_string)
        })
}

fn extract_context_length(repo_info: &Value) -> Option<u64> {
    repo_info
        .get("gguf")
        .and_then(|value| value.get("context_length"))
        .and_then(Value::as_u64)
        .or_else(|| {
            repo_info
                .get("cardData")
                .and_then(|value| value.get("context_length"))
                .and_then(Value::as_u64)
        })
        .or_else(|| {
            repo_info
                .get("config")
                .and_then(|value| value.get("max_position_embeddings"))
                .and_then(Value::as_u64)
        })
}

fn extract_parameter_size(repo_info: &Value) -> Option<String> {
    repo_info
        .get("gguf")
        .and_then(|value| value.get("parameter_size"))
        .and_then(Value::as_str)
        .map(ToString::to_string)
}

fn extract_quantization(file_name: &str) -> Option<String> {
    let lower = file_name.to_lowercase();
    let start = lower.find("q4")?;
    Some(
        lower[start..]
            .split(|c: char| !c.is_ascii_alphanumeric() && c != '_')
            .next()
            .unwrap_or("")
            .to_uppercase(),
    )
}

fn select_best_gguf(files: &Value) -> Option<(String, u64, Option<String>)> {
    let siblings = files.as_array()?;
    let mut best: Option<(String, u64, Option<String>, i32)> = None;

    for sibling in siblings {
        let file_name = sibling
            .get("path")
            .or_else(|| sibling.get("rfilename"))
            .and_then(Value::as_str)?
            .to_string();
        if !file_name.to_lowercase().ends_with(".gguf") {
            continue;
        }
        let lower = file_name.to_lowercase();
        if lower.contains("mmproj") || lower.contains("imatrix") {
            continue;
        }
        let size = sibling
            .get("size")
            .and_then(Value::as_u64)
            .or_else(|| {
                sibling
                    .get("lfs")
                    .and_then(|value| value.get("size"))
                    .and_then(Value::as_u64)
            })
            .unwrap_or(0);
        let sha = sibling
            .get("lfs")
            .and_then(|value| value.get("oid"))
            .and_then(Value::as_str)
            .map(ToString::to_string);
        let score = search_score(&file_name);
        let take = best
            .as_ref()
            .map(|(_, _, _, current)| score > *current)
            .unwrap_or(true);
        if take {
            best = Some((file_name, size, sha, score));
        }
    }

    best.map(|(file_name, size, sha, _)| (file_name, size, sha))
}

fn is_llm_candidate(repo_info: &Value) -> bool {
    let tags = vec_string_field(repo_info, "tags")
        .into_iter()
        .map(|tag| tag.to_lowercase())
        .collect::<Vec<_>>();
    let pipeline = repo_info
        .get("pipeline_tag")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_lowercase();

    if tags.iter().any(|tag| {
        tag == "conversational" || tag == "text-generation" || tag == "image-text-to-text"
    }) {
        return true;
    }
    if pipeline == "text-generation"
        || pipeline == "image-text-to-text"
        || pipeline == "conversational"
    {
        return true;
    }
    !matches!(
        pipeline.as_str(),
        "feature-extraction"
            | "automatic-speech-recognition"
            | "text-to-speech"
            | "sentence-similarity"
    )
}

async fn search_repo_ids_with_filters(
    client: &Client,
    search: Option<&str>,
    filtered: bool,
) -> Result<Vec<String>, String> {
    let mut url = format!("{HF_API_BASE}/models?sort=downloads&direction=-1&limit=24");
    if let Some(search) = search {
        if !search.trim().is_empty() {
            url.push_str("&search=");
            url.push_str(&urlencoding::encode(search.trim()));
        }
    }
    if filtered {
        url.push_str("&filter=gguf");
    }
    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("huggingface search failed: {e}"))?;
    if !response.status().is_success() {
        return Err(format!(
            "huggingface search failed: HTTP {}",
            response.status()
        ));
    }
    let items = response
        .json::<Vec<Value>>()
        .await
        .map_err(|e| format!("parse huggingface search results: {e}"))?;
    Ok(items
        .into_iter()
        .filter_map(|item| {
            item.get("id")
                .and_then(Value::as_str)
                .map(ToString::to_string)
        })
        .collect())
}

async fn fetch_repo_info(client: &Client, repo_id: &str) -> Result<Value, String> {
    let url = format!(
        "{HF_API_BASE}/models/{repo_id}?expand%5B%5D=gguf&expand%5B%5D=cardData&expand%5B%5D=config&expand%5B%5D=tags&expand%5B%5D=pipeline_tag"
    );
    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("huggingface model info failed for {repo_id}: {e}"))?;
    if !response.status().is_success() {
        return Err(format!(
            "huggingface model info failed for {repo_id}: HTTP {}",
            response.status()
        ));
    }
    response
        .json::<Value>()
        .await
        .map_err(|e| format!("parse huggingface model info for {repo_id}: {e}"))
}

async fn fetch_repo_tree(client: &Client, repo_id: &str) -> Result<Value, String> {
    let url = format!("{HF_API_BASE}/models/{repo_id}/tree/main?recursive=false&expand=true");
    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("huggingface file tree failed for {repo_id}: {e}"))?;
    if !response.status().is_success() {
        return Err(format!(
            "huggingface file tree failed for {repo_id}: HTTP {}",
            response.status()
        ));
    }
    response
        .json::<Value>()
        .await
        .map_err(|e| format!("parse huggingface file tree for {repo_id}: {e}"))
}

pub async fn list_local_model_catalog(
    state: &State<'_, AppState>,
    query: Option<String>,
) -> Result<Vec<LocalModelCatalogEntry>, String> {
    let client = http_client().await?;
    let mut repo_ids = Vec::new();
    let mut seen = HashSet::new();
    let query = query.unwrap_or_default().trim().to_string();
    let searches: Vec<(Option<String>, bool)> = if query.is_empty() {
        vec![
            (Some("gguf".to_string()), true),
            (Some("gguf".to_string()), false),
            (None, true),
            (None, false),
        ]
    } else {
        vec![
            (Some(query.clone()), true),
            (Some(format!("{query} gguf")), true),
            (Some(format!("{query} gguf")), false),
            (Some(query.clone()), false),
            (Some("gguf".to_string()), true),
        ]
    };

    for (search, filtered) in searches {
        let ids = search_repo_ids_with_filters(&client, search.as_deref(), filtered)
            .await
            .unwrap_or_default();
        for repo_id in ids {
            if seen.insert(repo_id.clone()) {
                repo_ids.push(repo_id);
            }
        }
        if !repo_ids.is_empty() {
            break;
        }
    }

    if repo_ids.is_empty() {
        return Err(
            "No GGUF models were returned from Hugging Face. Check your connection and try again."
                .to_string(),
        );
    }

    let existing = state.assets.get_status(None);
    let installed_ids: HashSet<String> = existing
        .into_iter()
        .filter(|asset| asset.asset_type.as_deref() == Some("local_model"))
        .filter(|asset| asset.downloaded && asset.verified)
        .map(|asset| asset.id)
        .collect();

    let mut entries = Vec::new();
    for repo_id in repo_ids.into_iter().take(24) {
        let repo_info = match fetch_repo_info(&client, &repo_id).await {
            Ok(value) => value,
            Err(_) => continue,
        };
        if !is_llm_candidate(&repo_info) {
            continue;
        }
        let tree_info = match fetch_repo_tree(&client, &repo_id).await {
            Ok(value) => value,
            Err(_) => continue,
        };
        let Some((file_name, size_bytes, sha256)) = select_best_gguf(&tree_info) else {
            continue;
        };
        if size_bytes == 0 {
            continue;
        }
        let family = family_label(&repo_id);
        let display_name = format!(
            "{} ({})",
            family_label(&repo_id),
            file_name.replace(".gguf", "")
        );
        let asset_id = asset_id_for(&repo_id, &file_name);
        let install_path = install_path_for(&repo_id, &file_name);
        let downloaded = installed_ids.contains(&asset_id);
        let tags = vec_string_field(&repo_info, "tags");
        let context_length = extract_context_length(&repo_info);
        let parameter_size = extract_parameter_size(&repo_info);
        let quantization = extract_quantization(&file_name);
        let license = extract_license(&repo_info);
        entries.push(LocalModelCatalogEntry {
            repo_id: repo_id.clone(),
            display_name,
            family,
            file_name: file_name.clone(),
            download_url: format!(
                "https://huggingface.co/{repo_id}/resolve/main/{}",
                urlencoding::encode(&file_name)
            ),
            size_bytes,
            expected_sha256: sha256,
            context_length,
            parameter_size,
            quantization,
            license,
            tags,
            asset_id,
            install_path,
            source_repo_url: model_page_url(&repo_id),
            installed: downloaded,
        });
    }

    if entries.is_empty() {
        return Err(
            "Hugging Face returned matching repos, but none exposed downloadable GGUF files."
                .to_string(),
        );
    }

    entries.sort_by(|a, b| {
        b.installed
            .cmp(&a.installed)
            .then_with(|| a.family.to_lowercase().cmp(&b.family.to_lowercase()))
            .then_with(|| a.size_bytes.cmp(&b.size_bytes))
    });
    Ok(entries)
}
