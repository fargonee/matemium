use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};

#[test]
fn ping_real_sidecar_binary() {
    let bin = match std::env::var("MATEMIUM_SIDECAR_BIN") {
        Ok(path) => path,
        Err(_) => {
            eprintln!("MATEMIUM_SIDECAR_BIN not set — skipping integration test");
            return;
        }
    };

    let mut child = Command::new(&bin)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .unwrap_or_else(|e| panic!("spawn {bin}: {e}"));

    let stdin = child.stdin.as_mut().expect("stdin");
    writeln!(
        stdin,
        r#"{{"type":"request","id":"1","command":"ping","params":{{}}}}"#
    )
    .expect("write ping");
    stdin.flush().expect("flush stdin");

    let stdout = child.stdout.take().expect("stdout");
    let mut reader = BufReader::new(stdout);
    let mut line = String::new();
    reader.read_line(&mut line).expect("read response");

    let parsed: serde_json::Value = serde_json::from_str(line.trim()).expect("parse response");
    assert_eq!(parsed["type"], "response");
    assert_eq!(parsed["id"], "1");
    assert_eq!(parsed["ok"], true);
    assert!(parsed["result"]["version"].is_string());

    let _ = child.kill();
    let _ = child.wait();
}
