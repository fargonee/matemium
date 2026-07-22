use matemium_desktop_lib::cloud::{chat, ChatCompletionRequest, ChatMessage};
use matemium_desktop_lib::commands::auth_login_inner;
use matemium_desktop_lib::workspace::{AppPaths, Settings};

fn server_base() -> String {
    std::env::var("MATEMIUM_SERVER_URL").unwrap_or_else(|_| "http://127.0.0.1:8080".to_string())
}

async fn server_healthy(base: &str) -> bool {
    match reqwest::get(format!("{base}/health")).await {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

fn sync_settings_server_url(paths: &AppPaths, base: &str) {
    let mut settings = paths.load_settings().expect("load settings");
    settings.server_url = base.to_string();
    paths
        .save_settings(&settings)
        .expect("save settings for test");
}

#[tokio::test]
async fn auth_login_command_path_returns_access_token() {
    let base = server_base();
    if !server_healthy(&base).await {
        eprintln!("Server not running at {base} — skipping auth_login command path test");
        return;
    }

    let paths = AppPaths::resolve().expect("resolve paths");
    paths.ensure().expect("ensure paths");
    sync_settings_server_url(&paths, &base);

    let token = auth_login_inner(&paths, "dev@matemium.app", "test")
        .await
        .expect("auth_login_inner (same path as auth_login invoke)");
    assert!(
        token.starts_with("dev."),
        "expected dev stub token, got {token}"
    );
}

#[tokio::test]
async fn auth_login_then_chat_sends_bearer_header() {
    let base = server_base();
    if !server_healthy(&base).await {
        eprintln!("Server not running at {base} — skipping bearer header test");
        return;
    }

    let paths = AppPaths::resolve().expect("resolve paths");
    paths.ensure().expect("ensure paths");
    sync_settings_server_url(&paths, &base);

    let token = auth_login_inner(&paths, "dev@matemium.app", "test")
        .await
        .expect("auth_login_inner");

    let settings = Settings {
        server_url: base.clone(),
        api_token: Some(token),
        ..Settings::default()
    };

    let response = chat(
        &settings,
        ChatCompletionRequest {
            messages: vec![ChatMessage {
                role: "user".to_string(),
                content: "add heading".to_string(),
                references: None,
            }],
            project_id: None,
            conversation_id: None,
            scenes_excerpt: None,
            llm_provider: None,
            use_personal_llm: None,
            model: None,
            use_autonomous_agent: None,
            agent_runtime_version: None,
        },
    )
    .await
    .expect("cloud::chat with Bearer token from auth_login_inner");

    assert_eq!(response.message.role, "assistant");
}
