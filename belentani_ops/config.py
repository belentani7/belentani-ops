import json
import os
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE", Path.home()))
PKG_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PKG_ROOT.parent

DEFAULT_CONFIG_PATHS = [
    PROJECT_ROOT / "belentani_ops.config.json",
    HOME / ".belentani" / "belentani_ops.config.json",
]

ALLOWED_HOME_DOTDIRS = {
    ".claude", ".opencode", ".agents", ".config", ".aider", ".codex",
    ".copilot", ".gemini", ".ollama", ".lmstudio", ".cursor", ".github",
    ".ssh", ".belentani", ".manus", ".cache", ".local", ".mcpjam",
    ".secrets", ".tools", ".venv", ".gitconfig", ".bashrc", ".profile",
    ".npm", ".cargo", ".bun", ".docker", ".kaggle", ".matplotlib",
    ".pytest_cache", ".next", ".netlify", ".railway", ".wrangler",
    ".azure", ".gnupg", ".m2", ".vscode", ".continue", ".cline",
    ".mimocode", ".morph", ".qwen", ".hermes", ".kiro", ".mimosa",
    ".memory", ".swarm", ".zen", ".vibe", ".wslconfig", ".condarc",
    ".gitignore", ".git-credentials", ".python_history", ".node_repl_history",
}

JUNK_DOTDIRS = {
    ".trae", ".grok", ".pi", ".roo", ".pochi", ".bob", ".fx",
    ".zcode", ".ona", ".eliza", ".forge", ".mimosa-junk",
}

SECRET_PATTERNS = [
    ("alibaba_sp", r"sk-sp-[A-Za-z0-9]{16,}"),
    ("alibaba", r"sk-[A-Za-z0-9]{20,}"),
    ("openrouter", r"sk-or-[A-Za-z0-9\-_]{16,}"),
    ("groq", r"gsk_[A-Za-z0-9]{20,}"),
    ("huggingface", r"hf_[A-Za-z0-9]{20,}"),
    ("openai", r"sk-proj-[A-Za-z0-9\-_]{20,}"),
    ("anthropic", r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    ("google", r"AIza[A-Za-z0-9\-_]{30,}"),
    ("aws", r"AKIA[A-Z0-9]{16}"),
    ("github_pat", r"gh[pousr]_[A-Za-z0-9]{30,}"),
    ("slack", r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    ("private_key", r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
]

DEFAULT_SITES = [
    "https://belentani7.github.io/belentani_Omega/",
    "https://belentani7.github.io/judas-experience/",
    "https://belentani7.github.io/ManosAbiertas/",
    "https://belentani7.github.io/Cruzando-el-charco/",
    "https://belentani7.github.io/duck-music-lab/",
    "https://belentani7.github.io/Belentani.cv-ai/",
    "https://belentani7.github.io/tender-words-connect/",
    "https://belentani7.github.io/ivy-la-vie/",
    "https://belentani7.github.io/CARQUIDEC/",
]

DEFAULT_PROVIDERS = {
    "alibaba_tokenplan": {
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "key_env": "DASHSCOPE_API_KEY",
        "models": ["qwen3.8-max", "qwen3.7-plus", "qwen3.6-flash"],
        "tier": "flat",
    },
    "alibaba_standard": {
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "key_env": "DASHSCOPE_API_KEY",
        "models": ["qwen-image-3.0", "wan3.0", "qwen-audio-3.0"],
        "tier": "metered",
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/models",
        "key_env": "HF_API_KEY",
        "models": ["ACE-Step", "Demucs", "CodeLlama"],
        "tier": "free",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "models": ["openai/gpt-4", "anthropic/claude-3.5-sonnet"],
        "tier": "metered",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "tier": "free",
    },
    "omniroute": {
        "base_url": "http://localhost:20128/v1",
        "key_env": None,
        "models": ["auto"],
        "tier": "local",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "key_env": None,
        "models": ["auto"],
        "tier": "local",
    },
}

TASK_ROUTES = {
    "coding": ["ollama", "omniroute", "alibaba_tokenplan", "groq", "openrouter"],
    "reasoning": ["alibaba_tokenplan", "openrouter", "groq", "ollama"],
    "fast": ["groq", "alibaba_tokenplan", "ollama"],
    "vision": ["alibaba_standard", "openrouter"],
    "audio": ["alibaba_standard", "huggingface"],
    "video": ["alibaba_standard"],
    "embedding": ["ollama", "alibaba_tokenplan"],
}

DEFAULT_BACKUP_REPOS = [
    HOME / "Documents" / "BELENTANI-OS",
    HOME / "Desktop" / "belentani_Omega-live",
]

DEFAULT_CLEAN_TARGETS = [
    HOME / "AppData" / "Local" / "Temp",
    Path("C:/Windows/Temp"),
    HOME / "AppData" / "Local" / "pip" / "cache",
    HOME / "AppData" / "Local" / "npm-cache",
    HOME / "AppData" / "Local" / "Microsoft" / "Windows" / "INetCache",
    HOME / "AppData" / "Local" / "Microsoft" / "Windows" / "Explorer",
    HOME / "AppData" / "Local" / "D3DSCache",
]


@dataclass
class Config:
    disk_warn_gb: float = 10.0
    disk_block_gb: float = 5.0
    disk_readonly_gb: float = 2.0
    sites: list = field(default_factory=lambda: list(DEFAULT_SITES))
    providers: dict = field(default_factory=lambda: dict(DEFAULT_PROVIDERS))
    backup_repos: list = field(default_factory=list)
    clean_targets: list = field(default_factory=list)
    github_user: str = "belentani7"
    monitor_timeout: float = 20.0
    scan_roots: list = field(default_factory=list)
    alert_webhook: str = ""

    def __post_init__(self):
        if not self.backup_repos:
            self.backup_repos = [str(p) for p in DEFAULT_BACKUP_REPOS]
        if not self.clean_targets:
            self.clean_targets = [str(p) for p in DEFAULT_CLEAN_TARGETS]
        if not self.scan_roots:
            self.scan_roots = [
                str(PROJECT_ROOT),
                str(HOME / ".belentani"),
                str(HOME / "Desktop"),
                str(HOME / "Documents"),
            ]

    def to_dict(self):
        return {
            "disk_warn_gb": self.disk_warn_gb,
            "disk_block_gb": self.disk_block_gb,
            "disk_readonly_gb": self.disk_readonly_gb,
            "sites": self.sites,
            "providers": self.providers,
            "backup_repos": self.backup_repos,
            "clean_targets": self.clean_targets,
            "github_user": self.github_user,
            "monitor_timeout": self.monitor_timeout,
            "scan_roots": self.scan_roots,
            "alert_webhook": self.alert_webhook,
        }


def load_config(path=None):
    candidates = [Path(path)] if path else list(DEFAULT_CONFIG_PATHS)
    for candidate in candidates:
        try:
            if candidate.is_file():
                data = json.loads(candidate.read_text(encoding="utf-8"))
                return Config(**{k: v for k, v in data.items() if k in Config().to_dict()}), candidate
        except Exception:
            continue
    return Config(), None


def save_config(cfg, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return p
