use matemium_desktop_lib::cloud::{login, ChatCompletionRequest, ChatMessage};
use matemium_desktop_lib::workspace::Settings;

fn server_base() -> String {
    std::env::var("MATEMIUM_SERVER_URL").unwrap_or_else(|_| "http://127.0.0.1:8080".to_string())
}

#[tokio::test]
async fn auth_and_chat_against_stub_server() {
    let base = server_base();
    let health = match reqwest::get(format!("{base}/health")).await {
        Ok(response) => response,
        Err(err) => {
            eprintln!("Server not running at {base} ({err}) — skipping auth integration test");
            return;
        }
    };
    if !health.status().is_success() {
        eprintln!("Server not running at {base} — skipping auth integration test");
        return;
    }

    let settings = Settings {
        server_url: base,
        api_token: None,
        ..Settings::default()
    };

    let token = login(&settings, "dev@matemium.app", "test")
        .await
        .expect("login");
    assert!(token.starts_with("dev."));

    let mut authed = settings.clone();
    authed.api_token = Some(token);

    let response = matemium_desktop_lib::cloud::chat(
        &authed,
        ChatCompletionRequest {
            messages: vec![ChatMessage {
                role: "user".to_string(),
                content: "Add a heading".to_string(),
                references: None,
            }],
            project_id: None,
            conversation_id: None,
            scenes_excerpt: Some("class MyScene(CanvasScene): pass".to_string()),
            llm_provider: None,
            use_personal_llm: None,
            model: None,
            use_autonomous_agent: None,
            agent_runtime_version: None,
        },
    )
    .await
    .expect("chat");

    assert_eq!(response.message.role, "assistant");
    assert!(response.code_edit.is_some() || !response.message.content.is_empty());
}
