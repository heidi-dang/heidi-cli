use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use tempfile::TempDir;

fn fdx_bin() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    // Try debug first (cargo test), then release (cargo test --release)
    let debug = manifest.join("../../target/debug/fdx");
    if debug.exists() {
        return debug;
    }
    manifest.join("../../target/release/fdx")
}

fn git(repo: &Path, args: &[&str]) {
    let status = Command::new("git")
        .args(args)
        .current_dir(repo)
        .status()
        .expect("git command failed");
    assert!(status.success(), "git {:?} failed", args);
}

fn fixture_repo() -> TempDir {
    let dir = tempfile::tempdir().expect("temp git repo");
    git(dir.path(), &["init", "-q"]);
    git(
        dir.path(),
        &["config", "user.email", "fdx-test@example.invalid"],
    );
    git(dir.path(), &["config", "user.name", "FDX Test"]);
    fs::write(dir.path().join("README.md"), "# fixture\n").expect("fixture write");
    git(dir.path(), &["add", "README.md"]);
    git(dir.path(), &["commit", "-q", "-m", "fixture"]);
    dir
}

#[test]
fn test_git_status() {
    let repo = fixture_repo();
    let output = Command::new(fdx_bin())
        .args(["git", "status"])
        .current_dir(repo.path())
        .output()
        .expect("fdx git status failed");

    let stdout = String::from_utf8_lossy(&output.stdout);
    // Should show either clean or some status groups
    assert!(
        stdout.contains("clean")
            || stdout.contains("staged")
            || stdout.contains("unstaged")
            || stdout.contains("untracked"),
        "should show status: {}",
        stdout
    );
    assert!(output.status.success());
}

#[test]
fn test_git_log() {
    let repo = fixture_repo();
    let output = Command::new(fdx_bin())
        .args(["git", "log", "-n", "3"])
        .current_dir(repo.path())
        .output()
        .expect("fdx git log failed");

    let stdout = String::from_utf8_lossy(&output.stdout);
    // Should show commit SHAs (7 hex chars)
    assert!(stdout.len() > 20, "should have log output: {}", stdout);
    assert!(output.status.success());
}

#[test]
fn test_git_branch() {
    let repo = fixture_repo();
    let output = Command::new(fdx_bin())
        .args(["git", "branch"])
        .current_dir(repo.path())
        .output()
        .expect("fdx git branch failed");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let has_branch = stdout
        .lines()
        .any(|line| line.trim_start_matches('\u{1b}').contains("* "))
        || stdout.contains("HEAD");
    assert!(has_branch, "should show current branch or HEAD: {}", stdout);
    assert!(output.status.success());
}

#[test]
fn test_git_pass_through() {
    // Test that allowed subcommands pass through.
    let repo = fixture_repo();
    let output = Command::new(fdx_bin())
        .args(["git", "rev-parse", "--is-inside-work-tree"])
        .current_dir(repo.path())
        .output()
        .expect("fdx git rev-parse failed");

    assert!(output.status.success(), "git rev-parse should succeed");
}
