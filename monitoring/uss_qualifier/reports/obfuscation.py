import json
import os
import re
import shutil
import tempfile
import zipfile
from typing import Any
from urllib.parse import urlparse

from implicitdict import ImplicitDict
from loguru import logger

WHITELIST_HOSTNAMES = {
    "127.0.0.1",
    "github.com",
    "localhost",
    "maps.google.com",
    "raw.githubusercontent.com",
    "schemas.openapi.org",
    "w3.org",
    "www.google.com",
    "www.opengis.net",
    "www.w3.org",
}


class ObfuscatorConfig(ImplicitDict):
    obfuscate_participants: bool = True
    obfuscate_hostnames: bool = True
    obfuscate_tokens: bool = True


def find_urls(text: str) -> list[str]:
    # Match strings starting with http:// or https://
    pattern = r"https?://[a-zA-Z0-9.:/\-_~%#?=&@+;!*()\[\]]+"
    raw_urls = re.findall(pattern, text)
    cleaned_urls = []
    for url in raw_urls:
        while url and url[-1] in (".", ",", ";", "?", "!", ")", "]", ">"):
            url = url[:-1]
        if url:
            cleaned_urls.append(url)
    return cleaned_urls


def get_hostname(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def scan_json(obj, participant_ids: set[str], hostnames: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("participant_id", "participant") and isinstance(v, str):
                participant_ids.add(v)
            elif k in ("participants", "participant_ids") and isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        participant_ids.add(item)
            elif k in (
                "participant_requirements",
                "aggregate_participants",
                "participant_verifications",
            ) and isinstance(v, dict):
                for p_id in v.keys():
                    participant_ids.add(p_id)
                if k == "aggregate_participants":
                    for sub_list in v.values():
                        if isinstance(sub_list, list):
                            for p_id in sub_list:
                                if isinstance(p_id, str):
                                    participant_ids.add(p_id)
            elif k == "manager" and isinstance(v, str):
                participant_ids.add(v)
            elif isinstance(v, str):
                for url in find_urls(v):
                    h = get_hostname(url)
                    if h:
                        hostnames.add(h)
            scan_json(v, participant_ids, hostnames)
    elif isinstance(obj, list):
        for item in obj:
            scan_json(item, participant_ids, hostnames)


def scan_text(text: str, hostnames: set[str]):
    for url in find_urls(text):
        h = get_hostname(url)
        if h:
            hostnames.add(h)


def obfuscate_string(
    s: str,
    participant_map: dict[str, str],
    hostname_map: dict[str, str],
    config: ObfuscatorConfig,
) -> str:
    if not s:
        return s

    # 1. Obfuscate tokens
    if config.obfuscate_tokens:
        s = re.sub(r"(?i)\bBearer\s+\S+", "Bearer REDACTED", s)

    # 2. Obfuscate hostnames
    if config.obfuscate_hostnames:
        for h, mapped_h in hostname_map.items():
            s = re.sub(rf"\b{re.escape(h)}\b", mapped_h, s)

    # 3. Obfuscate participants
    if config.obfuscate_participants:
        for pid, mapped_pid in participant_map.items():
            s = re.sub(rf"\b{re.escape(pid)}\b", mapped_pid, s)

    return s


def obfuscate_json_obj(
    obj,
    participant_map: dict[str, str],
    hostname_map: dict[str, str],
    config: ObfuscatorConfig,
) -> Any:
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_k = obfuscate_string(k, participant_map, hostname_map, config)
            if (
                config.obfuscate_tokens
                and new_k.lower() == "authorization"
                and isinstance(v, str)
            ):
                if v.lower().startswith("bearer "):
                    new_dict[new_k] = "Bearer REDACTED"
                else:
                    new_dict[new_k] = "REDACTED"
            else:
                new_dict[new_k] = obfuscate_json_obj(
                    v, participant_map, hostname_map, config
                )
        return new_dict
    elif isinstance(obj, list):
        return [
            obfuscate_json_obj(item, participant_map, hostname_map, config)
            for item in obj
        ]
    elif isinstance(obj, str):
        return obfuscate_string(obj, participant_map, hostname_map, config)
    else:
        return obj


def obfuscate_path_component(
    name: str, participant_map: dict[str, str], config: ObfuscatorConfig
) -> str:
    if config.obfuscate_participants:
        for pid, mapped_pid in participant_map.items():
            name = re.sub(rf"\b{re.escape(pid)}\b", mapped_pid, name)
    return name


def obfuscate_relative_path(
    rel_path: str, participant_map: dict[str, str], config: ObfuscatorConfig
) -> str:
    parts = rel_path.split(os.sep)
    obfuscated_parts = [
        obfuscate_path_component(p, participant_map, config) for p in parts
    ]
    return os.sep.join(obfuscated_parts)


def obfuscate_directory(
    input_dir: str, output_dir: str, config: ObfuscatorConfig
) -> None:
    # Pass 1: Learn/scan
    participant_ids = set()
    hostnames = set()

    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if file.lower().endswith(".json"):
                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        data = json.load(f)
                    scan_json(data, participant_ids, hostnames)
                except Exception as e:
                    logger.warning(f"Failed to scan JSON file {file_path}: {e}")
            elif file.lower().endswith((".html", ".kml", ".yaml", ".yml", ".md")):
                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    scan_text(content, hostnames)
                except Exception as e:
                    logger.warning(f"Failed to scan text file {file_path}: {e}")

    # Clean participant IDs and hostnames
    participant_ids = {p for p in participant_ids if p}
    hostnames = {h for h in hostnames if h and h not in WHITELIST_HOSTNAMES}

    # Generate maps
    participant_map = {}
    for idx, pid in enumerate(
        sorted(sorted(participant_ids), key=len, reverse=True), start=1
    ):
        participant_map[pid] = f"participant{idx}"

    hostname_map = {}
    for idx, h in enumerate(sorted(sorted(hostnames), key=len, reverse=True), start=1):
        hostname_map[h] = f"host{idx}"

    logger.info(f"Detected participants to obfuscate: {list(participant_map.keys())}")
    logger.info(f"Detected hostnames to obfuscate: {list(hostname_map.keys())}")

    # Pass 2: Write obfuscated files
    for root, _, files in os.walk(input_dir):
        for file in files:
            input_file_path = os.path.join(root, file)
            rel_path = os.path.relpath(input_file_path, input_dir)
            obf_rel_path = obfuscate_relative_path(rel_path, participant_map, config)
            output_file_path = os.path.join(output_dir, obf_rel_path)

            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

            if file.lower().endswith(".json"):
                try:
                    with open(input_file_path, encoding="utf-8", errors="replace") as f:
                        sample = f.read(100)
                        pretty = "\n" in sample
                        f.seek(0)
                        data = json.load(f)
                    obfuscated_data = obfuscate_json_obj(
                        data, participant_map, hostname_map, config
                    )
                    with open(output_file_path, "w", encoding="utf-8") as f:
                        if pretty:
                            json.dump(obfuscated_data, f, indent=2)
                        else:
                            json.dump(obfuscated_data, f)
                except Exception as e:
                    logger.error(
                        f"Failed to obfuscate JSON file {input_file_path}: {e}"
                    )
            elif file.lower().endswith((".html", ".kml", ".yaml", ".yml", ".md")):
                try:
                    with open(input_file_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    obfuscated_content = obfuscate_string(
                        content, participant_map, hostname_map, config
                    )
                    with open(output_file_path, "w", encoding="utf-8") as f:
                        f.write(obfuscated_content)
                except Exception as e:
                    logger.error(
                        f"Failed to obfuscate text file {input_file_path}: {e}"
                    )
            else:
                try:
                    shutil.copy2(input_file_path, output_file_path)
                except Exception as e:
                    logger.error(f"Failed to copy file {input_file_path}: {e}")


def obfuscate_artifacts(
    input_path: str, output_path: str, config: ObfuscatorConfig
) -> None:
    input_is_zip = zipfile.is_zipfile(input_path) or input_path.lower().endswith(".zip")
    output_is_zip = output_path.lower().endswith(".zip")

    with (
        tempfile.TemporaryDirectory() as tmp_in_dir,
        tempfile.TemporaryDirectory() as tmp_out_dir,
    ):
        if input_is_zip:
            logger.info(f"Extracting input zip {input_path} to temporary directory")
            with zipfile.ZipFile(input_path, "r") as zip_ref:
                zip_ref.extractall(tmp_in_dir)
            actual_in_dir = tmp_in_dir
        else:
            actual_in_dir = input_path

        if output_is_zip:
            actual_out_dir = tmp_out_dir
        else:
            actual_out_dir = output_path
            os.makedirs(actual_out_dir, exist_ok=True)

        obfuscate_directory(actual_in_dir, actual_out_dir, config)

        if output_is_zip:
            logger.info(f"Packaging output to zip {output_path}")
            parent_dir = os.path.dirname(os.path.abspath(output_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_write:
                for root, _, files in os.walk(actual_out_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, actual_out_dir)
                        zip_write.write(full_path, rel_path)
