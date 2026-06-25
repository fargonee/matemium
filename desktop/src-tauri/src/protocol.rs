use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum InboundMessage {
    Response {
        id: String,
        ok: bool,
        #[serde(default)]
        result: Option<Value>,
        #[serde(default)]
        error: Option<Value>,
    },
    Event {
        event: String,
        #[serde(default)]
        data: Value,
    },
}

pub fn build_request(id: &str, command: &str, params: Value) -> String {
    let envelope = json!({
        "type": "request",
        "id": id,
        "command": command,
        "params": params,
    });
    format!("{envelope}\n")
}

pub fn parse_line(line: &str) -> Option<InboundMessage> {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return None;
    }
    serde_json::from_str(trimmed).ok()
}

pub fn response_error_message(error: &Value) -> String {
    error
        .get("message")
        .and_then(|v| v.as_str())
        .or_else(|| error.as_str())
        .unwrap_or("sidecar request failed")
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn build_request_includes_trailing_newline() {
        let line = build_request("abc", "ping", json!({}));
        assert!(line.ends_with('\n'));
        let parsed: Value = serde_json::from_str(line.trim()).unwrap();
        assert_eq!(parsed["command"], "ping");
        assert_eq!(parsed["id"], "abc");
    }

    #[test]
    fn parse_response_roundtrip() {
        let raw = r#"{"type":"response","id":"1","ok":true,"result":{"version":"0.1.0"}}"#;
        let msg = parse_line(raw).expect("parse");
        match msg {
            InboundMessage::Response { id, ok, result, .. } => {
                assert_eq!(id, "1");
                assert!(ok);
                assert_eq!(result.unwrap()["version"], "0.1.0");
            }
            _ => panic!("expected response"),
        }
    }

    #[test]
    fn parse_event_roundtrip() {
        let raw = r#"{"type":"event","event":"render_progress","data":{"pct":0.5}}"#;
        let msg = parse_line(raw).expect("parse");
        match msg {
            InboundMessage::Event { event, data } => {
                assert_eq!(event, "render_progress");
                assert_eq!(data["pct"], 0.5);
            }
            _ => panic!("expected event"),
        }
    }
}