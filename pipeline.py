"""Cross-platform subprocess orchestrator for the mental-health NLP pipeline."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parent
LOG_ROOT = ROOT / "pipeline_logs"
SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Hydration:
    """How to reconstruct one native CSV artifact from delivery chunks."""

    target: Path
    directory: Path
    base_name: str


@dataclass(frozen=True)
class Stage:
    name: str
    group: str
    script: Path | None = None
    args: tuple[str, ...] = ()
    outputs: tuple[Path, ...] = ()
    dependencies: tuple[str, ...] = ()
    hydrations: tuple[Hydration, ...] = ()
    capture_output: Path | None = None
    action: Callable[[], None] | None = None

    @property
    def cwd(self) -> Path:
        if self.script is None:
            return ROOT
        return self.script.parent


def p(relative: str) -> Path:
    return ROOT / Path(relative)


STEP2 = p("Step 2 - Raw Data EDA")
STEP3 = p("Step 3 - Unified Dataset")
STEP4 = p("Step 4 - Cleaning")
STEP5 = p("Step 5 - Text Preprocessing")
STEP6 = p("Step 6 - EDA on Cleaned Data")
STEP7 = p("Step 7 - Feature Extraction")
STEP8 = p("Step 8 - Class Imbalance Handling")
STEP9 = p("Step 9 - Model Training")
STEP10 = p("Step 10 - Evaluation")
STEP11 = p("Step 11 - Explainability and Error Analysis")
STEP12 = p("Step 12 - Packaging")


PACKAGE_ARTIFACT_SOURCES = {
    STEP12 / "package/mental_health_screening/artifacts/primary_xgboost.pkl":
        STEP9 / "output/models/primary_dataset_xgboost.pkl",
    STEP12 / "package/mental_health_screening/artifacts/primary_tfidf_vectorizer.pkl":
        STEP7 / "output/primary_dataset_tfidf_vectorizer.pkl",
    STEP12 / "package/mental_health_screening/artifacts/primary_chi2_selector.pkl":
        STEP9 / "output/models/primary_dataset_chi2_selector.pkl",
    STEP12 / "package/mental_health_screening/artifacts/urgency_logreg.pkl":
        STEP9 / "output/models/urgency_dataset_logreg.pkl",
    STEP12 / "package/mental_health_screening/artifacts/urgency_tfidf_vectorizer.pkl":
        STEP7 / "output/urgency_dataset_tfidf_vectorizer.pkl",
    STEP12 / "package/mental_health_screening/artifacts/curated_urgency_keywords.json":
        STEP6 / "findings/urgency_keyword_candidates.json",
    STEP12 / "package/mental_health_screening/artifacts/emotion_lexicon.json":
        STEP7 / "output/emotion_lexicon.json",
}


def sync_package_artifacts() -> None:
    """Copy the fitted artifacts into the standalone inference package."""

    missing = [source for source in PACKAGE_ARTIFACT_SOURCES.values() if not source.is_file()]
    if missing:
        rendered = "\n".join(f"  - {path.relative_to(ROOT)}" for path in missing)
        raise RuntimeError(f"Cannot package; source artifacts are missing:\n{rendered}")

    for destination, source in PACKAGE_ARTIFACT_SOURCES.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
        print(f"copied {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")


STAGES: tuple[Stage, ...] = (
    Stage(
        "raw-eda", "prepare", STEP2 / "code/eda_raw_datasets.py",
        outputs=(STEP2 / "findings/eda_output_log.txt",),
        capture_output=STEP2 / "findings/eda_output_log.txt",
    ),
    Stage(
        "overlap-check", "prepare", STEP2 / "code/check_cross_dataset_overlap.py",
        outputs=(STEP2 / "findings/cross_dataset_overlap_log.txt",),
        capture_output=STEP2 / "findings/cross_dataset_overlap_log.txt",
    ),
    Stage(
        "unify", "prepare", STEP3 / "code/build_unified_dataset.py",
        outputs=(STEP3 / "output/primary_dataset.csv", STEP3 / "output/urgency_dataset.csv"),
        hydrations=(
            Hydration(STEP3 / "output/primary_dataset.csv", STEP3 / "output", "primary_dataset"),
            Hydration(STEP3 / "output/urgency_dataset.csv", STEP3 / "output", "urgency_dataset"),
        ),
    ),
    Stage(
        "clean", "prepare", STEP4 / "code/clean_datasets.py",
        outputs=(STEP4 / "output/primary_dataset_clean.csv", STEP4 / "output/urgency_dataset_clean.csv"),
        dependencies=("unify",),
        hydrations=(
            Hydration(STEP4 / "output/primary_dataset_clean.csv", STEP4 / "output", "primary_dataset_clean"),
            Hydration(STEP4 / "output/urgency_dataset_clean.csv", STEP4 / "output", "urgency_dataset_clean"),
        ),
    ),
    Stage(
        "preprocess-primary", "prepare", STEP5 / "code/preprocess_text.py", ("primary",),
        outputs=(STEP5 / "output/primary_dataset_clean_preprocessed.csv",),
        dependencies=("clean",),
        hydrations=(Hydration(
            STEP5 / "output/primary_dataset_clean_preprocessed.csv",
            STEP5 / "output", "primary_dataset_preprocessed",
        ),),
    ),
    Stage(
        "preprocess-urgency", "prepare", STEP5 / "code/preprocess_text.py", ("urgency",),
        outputs=(STEP5 / "output/urgency_dataset_clean_preprocessed.csv",),
        dependencies=("clean",),
        hydrations=(Hydration(
            STEP5 / "output/urgency_dataset_clean_preprocessed.csv",
            STEP5 / "output", "urgency_dataset_preprocessed",
        ),),
    ),
    Stage(
        "cleaned-eda", "prepare", STEP6 / "code/eda_cleaned_data.py",
        outputs=(
            STEP6 / "findings/eda_cleaned_report.txt",
            STEP6 / "findings/garbage_flagged_rows.csv",
            STEP6 / "findings/likely_non_english_sample.txt",
            STEP6 / "findings/urgency_keyword_candidates.json",
        ),
        dependencies=("preprocess-primary", "preprocess-urgency"),
    ),
    Stage(
        "emotion-lexicon", "prepare", STEP7 / "code/build_emotion_lexicon.py",
        outputs=(STEP7 / "output/emotion_lexicon.json",), dependencies=("unify",),
    ),
    Stage(
        "features-primary", "prepare", STEP7 / "code/feature_engineering.py", ("primary",),
        outputs=(STEP7 / "output/primary_dataset_clean_preprocessed_handcrafted_features.csv.gz",),
        dependencies=("preprocess-primary", "cleaned-eda", "emotion-lexicon"),
        hydrations=(Hydration(
            STEP7 / "output/primary_dataset_clean_preprocessed_handcrafted_features.csv.gz",
            STEP7 / "output", "primary_dataset_features",
        ),),
    ),
    Stage(
        "features-urgency", "prepare", STEP7 / "code/feature_engineering.py", ("urgency",),
        outputs=(STEP7 / "output/urgency_dataset_clean_preprocessed_handcrafted_features.csv.gz",),
        dependencies=("preprocess-urgency", "cleaned-eda", "emotion-lexicon"),
        hydrations=(Hydration(
            STEP7 / "output/urgency_dataset_clean_preprocessed_handcrafted_features.csv.gz",
            STEP7 / "output", "urgency_dataset_features",
        ),),
    ),
    Stage(
        "tfidf-primary", "prepare", STEP7 / "code/tfidf_vectorize.py", ("primary",),
        outputs=(
            STEP7 / "output/primary_dataset_tfidf_train.npz",
            STEP7 / "output/primary_dataset_tfidf_val.npz",
            STEP7 / "output/primary_dataset_tfidf_test.npz",
            STEP7 / "output/primary_dataset_tfidf_vectorizer.pkl",
        ),
        dependencies=("preprocess-primary", "cleaned-eda"),
    ),
    Stage(
        "tfidf-urgency", "prepare", STEP7 / "code/tfidf_vectorize.py", ("urgency",),
        outputs=(
            STEP7 / "output/urgency_dataset_tfidf_train.npz",
            STEP7 / "output/urgency_dataset_tfidf_val.npz",
            STEP7 / "output/urgency_dataset_tfidf_test.npz",
            STEP7 / "output/urgency_dataset_tfidf_vectorizer.pkl",
        ),
        dependencies=("preprocess-urgency", "cleaned-eda"),
    ),
    Stage(
        "class-weights", "prepare", STEP8 / "code/compute_class_weights.py",
        outputs=(STEP8 / "output/class_weights.json",),
        dependencies=("features-primary", "features-urgency"),
    ),
    Stage(
        "baselines-primary", "train", STEP9 / "code/train_baselines.py", ("primary",),
        outputs=(
            STEP9 / "output/metrics/primary_dataset_baselines.json",
            STEP9 / "output/models/primary_dataset_logreg.pkl",
            STEP9 / "output/models/primary_dataset_linear_svm.pkl",
        ),
        dependencies=("features-primary", "tfidf-primary", "class-weights"),
    ),
    Stage(
        "baselines-urgency", "train", STEP9 / "code/train_baselines.py", ("urgency",),
        outputs=(
            STEP9 / "output/metrics/urgency_dataset_baselines.json",
            STEP9 / "output/models/urgency_dataset_logreg.pkl",
            STEP9 / "output/models/urgency_dataset_linear_svm.pkl",
        ),
        dependencies=("features-urgency", "tfidf-urgency", "class-weights"),
    ),
    Stage(
        "midtier-primary", "train", STEP9 / "code/train_midtier.py", ("primary", "both"),
        outputs=(
            STEP9 / "output/metrics/primary_dataset_midtier.json",
            STEP9 / "output/models/primary_dataset_chi2_selector.pkl",
            STEP9 / "output/models/primary_dataset_xgboost.pkl",
        ),
        dependencies=("features-primary", "tfidf-primary", "class-weights"),
    ),
    Stage(
        "midtier-urgency", "train", STEP9 / "code/train_midtier.py", ("urgency", "both"),
        outputs=(
            STEP9 / "output/metrics/urgency_dataset_midtier.json",
            STEP9 / "output/models/urgency_dataset_chi2_selector.pkl",
            STEP9 / "output/models/urgency_dataset_xgboost.pkl",
        ),
        dependencies=("features-urgency", "tfidf-urgency", "class-weights"),
    ),
    Stage(
        "evaluate", "train", STEP10 / "code/evaluate_test.py",
        outputs=(
            STEP10 / "output/primary_dataset_test_results.json",
            STEP10 / "output/urgency_dataset_test_results.json",
        ),
        dependencies=("midtier-primary", "baselines-urgency"),
    ),
    Stage(
        "confusion-plots", "train", STEP10 / "code/plot_confusion_matrices.py",
        outputs=(
            STEP10 / "output/primary_dataset_confusion_matrix.png",
            STEP10 / "output/urgency_dataset_confusion_matrix_default.png",
            STEP10 / "output/urgency_dataset_confusion_matrix_recommended.png",
        ),
        dependencies=("evaluate",),
    ),
    Stage(
        "error-analysis", "report", STEP11 / "code/error_analysis.py",
        outputs=(
            STEP11 / "output/error_analysis/primary_dataset_misclassified.csv",
            STEP11 / "output/error_analysis/primary_dataset_confusion_pairs.csv",
            STEP11 / "output/error_analysis/primary_dataset_example_misses.json",
            STEP11 / "output/error_analysis/urgency_dataset_false_negatives_at_0.15.csv",
            STEP11 / "output/error_analysis/urgency_dataset_false_positives_at_0.15.csv",
        ),
        dependencies=(
            "evaluate", "preprocess-primary", "preprocess-urgency",
            "features-primary", "features-urgency", "tfidf-primary", "tfidf-urgency",
        ),
    ),
    Stage(
        "shap-analysis", "report", STEP11 / "code/explainability_shap.py",
        outputs=(
            STEP11 / "output/explainability/primary_dataset_shap_global_importance.csv",
            STEP11 / "output/explainability/primary_dataset_shap_reliable_terms.csv",
            STEP11 / "output/explainability/urgency_dataset_shap_global_importance.csv",
            STEP11 / "output/explainability/urgency_dataset_shap_reliable_terms.csv",
            STEP11 / "output/explainability/urgency_dataset_shap_top_terms.json",
        ),
        dependencies=(
            "evaluate", "cleaned-eda", "emotion-lexicon",
            "features-primary", "features-urgency", "tfidf-primary", "tfidf-urgency",
        ),
    ),
    Stage(
        "shap-plots", "report", STEP11 / "code/plot_shap_summary.py",
        outputs=(
            STEP11 / "output/explainability/primary_dataset_shap_bar.png",
            STEP11 / "output/explainability/primary_dataset_shap_reliable_bar.png",
            STEP11 / "output/explainability/urgency_dataset_shap_bar.png",
            STEP11 / "output/explainability/urgency_dataset_shap_reliable_bar.png",
        ),
        dependencies=("shap-analysis",),
    ),
    Stage(
        "package-artifacts", "report", outputs=tuple(PACKAGE_ARTIFACT_SOURCES),
        dependencies=("evaluate", "cleaned-eda", "emotion-lexicon"), action=sync_package_artifacts,
    ),
    Stage(
        "package-config", "report", STEP12 / "code/write_config.py",
        outputs=(STEP12 / "package/mental_health_screening/artifacts/config.json",),
        dependencies=("package-artifacts", "features-primary", "features-urgency"),
    ),
    Stage(
        "package-verify", "report", STEP12 / "code/verify_parity.py",
        outputs=(STEP12 / "verify_parity_output.txt",),
        dependencies=(
            "package-config", "evaluate", "unify",
            "preprocess-primary", "preprocess-urgency",
            "features-primary", "features-urgency", "tfidf-primary", "tfidf-urgency",
        ),
        capture_output=STEP12 / "verify_parity_output.txt",
    ),
)

STAGE_BY_NAME = {stage.name: stage for stage in STAGES}
GROUPS = {
    "prepare": tuple(stage.name for stage in STAGES if stage.group == "prepare"),
    "train": tuple(stage.name for stage in STAGES if stage.group == "train"),
    "report": tuple(stage.name for stage in STAGES if stage.group == "report"),
    "all": tuple(stage.name for stage in STAGES),
}


def delivery_files(hydration: Hydration) -> tuple[Path, ...] | None:
    """Return a validated, ordered delivery chunk set, or None if incomplete."""

    ordered: list[Path] = []
    for split in SPLITS:
        single = hydration.directory / f"{hydration.base_name}_{split}.csv.gz"
        part_pattern = re.compile(
            rf"^{re.escape(hydration.base_name)}_{split}_part(\d+)of(\d+)\.csv\.gz$"
        )
        parts: list[tuple[int, int, Path]] = []
        if hydration.directory.is_dir():
            for candidate in hydration.directory.iterdir():
                match = part_pattern.match(candidate.name)
                if match:
                    parts.append((int(match.group(1)), int(match.group(2)), candidate))

        if single.is_file() and parts:
            return None
        if single.is_file():
            ordered.append(single)
            continue
        if not parts:
            return None

        totals = {total for _, total, _ in parts}
        if len(totals) != 1:
            return None
        total = totals.pop()
        indexes = [index for index, _, _ in parts]
        if len(indexes) != len(set(indexes)) or set(indexes) != set(range(1, total + 1)):
            return None
        ordered.extend(path for _, _, path in sorted(parts))
    return tuple(ordered)


def stage_state(stage: Stage) -> tuple[str, tuple[Path, ...]]:
    missing = tuple(path for path in stage.outputs if not path.is_file())
    if not missing:
        return "present", ()

    hydration_by_target = {item.target: item for item in stage.hydrations}
    if all(path in hydration_by_target and delivery_files(hydration_by_target[path]) for path in missing):
        return "hydratable", missing
    return "missing", missing


def hydrate_stage(stage: Stage) -> None:
    pending = [item for item in stage.hydrations if not item.target.is_file()]
    for hydration in pending:
        sources = delivery_files(hydration)
        if not sources:
            raise RuntimeError(f"Incomplete delivery chunks for {hydration.target.relative_to(ROOT)}")

        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("pandas is required to hydrate delivery chunks") from exc

        frames = []
        for source in sources:
            frame = pd.read_csv(source)
            split = next(value for value in SPLITS if f"_{value}" in source.name)
            if "split" not in frame.columns:
                frame["split"] = split
            elif not frame["split"].astype(str).eq(split).all():
                raise RuntimeError(f"Split column does not match filename: {source}")
            frames.append(frame)

        combined = pd.concat(frames, ignore_index=True)
        hydration.target.parent.mkdir(parents=True, exist_ok=True)
        temporary = hydration.target.with_name(hydration.target.name + ".tmp")
        compression = "gzip" if hydration.target.name.endswith(".gz") else None
        combined.to_csv(temporary, index=False, compression=compression)
        os.replace(temporary, hydration.target)
        print(
            f"[hydrate] {hydration.target.relative_to(ROOT)} "
            f"from {len(sources)} delivery file(s) ({len(combined):,} rows)"
        )


def ensure_dependencies(stage: Stage) -> None:
    for dependency_name in stage.dependencies:
        dependency = STAGE_BY_NAME[dependency_name]
        state, missing = stage_state(dependency)
        if state == "hydratable":
            hydrate_stage(dependency)
            state, missing = stage_state(dependency)
        if state != "present":
            rendered = ", ".join(str(path.relative_to(ROOT)) for path in missing)
            raise RuntimeError(
                f"Stage '{stage.name}' requires incomplete stage '{dependency_name}': {rendered}"
            )


def run_subprocess(stage: Stage, log_path: Path) -> int:
    assert stage.script is not None
    command = [sys.executable, str(stage.script), *stage.args]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[run] {' '.join(command)}")
    print(f"[cwd] {stage.cwd}")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    capture_tmp = None
    capture_handle = None
    if stage.capture_output is not None:
        stage.capture_output.parent.mkdir(parents=True, exist_ok=True)
        capture_tmp = stage.capture_output.with_name(stage.capture_output.name + ".tmp")
        capture_handle = capture_tmp.open("w", encoding="utf-8")

    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                command,
                cwd=stage.cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="")
                log_handle.write(line)
                if capture_handle is not None:
                    capture_handle.write(line)
            return_code = process.wait()
    finally:
        if capture_handle is not None:
            capture_handle.close()

    if return_code == 0 and capture_tmp is not None and stage.capture_output is not None:
        os.replace(capture_tmp, stage.capture_output)
    elif capture_tmp is not None:
        capture_tmp.unlink(missing_ok=True)
    return return_code


def selected_names(group: str, from_stage: str | None, to_stage: str | None) -> tuple[str, ...]:
    names = GROUPS[group]
    if from_stage is not None and from_stage not in names:
        raise ValueError(f"--from stage '{from_stage}' is not in group '{group}'")
    if to_stage is not None and to_stage not in names:
        raise ValueError(f"--to stage '{to_stage}' is not in group '{group}'")
    start = names.index(from_stage) if from_stage else 0
    end = names.index(to_stage) if to_stage else len(names) - 1
    if start > end:
        raise ValueError("--from must not occur after --to")
    return names[start:end + 1]


def run_pipeline(group: str, from_stage: str | None, to_stage: str | None, force: bool) -> int:
    try:
        names = selected_names(group, from_stage, to_stage)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    run_dir = LOG_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")
    for name in names:
        stage = STAGE_BY_NAME[name]
        try:
            state, _ = stage_state(stage)
            if not force and state == "present":
                print(f"[skip] {name}: outputs present")
                continue
            if not force and state == "hydratable":
                hydrate_stage(stage)
                print(f"[skip] {name}: restored from delivery chunks")
                continue

            ensure_dependencies(stage)

            for output in stage.outputs:
                output.parent.mkdir(parents=True, exist_ok=True)
            print(f"\n=== {name} ===")
            if stage.action is not None:
                stage.action()
                return_code = 0
            else:
                return_code = run_subprocess(stage, run_dir / f"{name}.log")
            if return_code != 0:
                print(f"[failed] {name}: exit code {return_code}", file=sys.stderr)
                return return_code

            state, missing = stage_state(stage)
            if state != "present":
                rendered = ", ".join(str(path.relative_to(ROOT)) for path in missing)
                print(f"[failed] {name}: expected outputs not created: {rendered}", file=sys.stderr)
                return 1
            print(f"[done] {name}")
        except (OSError, RuntimeError) as exc:
            print(f"[failed] {name}: {exc}", file=sys.stderr)
            return 1
    return 0


def print_status(group: str) -> int:
    print(f"Pipeline status ({group})")
    print(f"Repository: {ROOT}")
    for name in GROUPS[group]:
        stage = STAGE_BY_NAME[name]
        state, missing = stage_state(stage)
        print(f"{name:<24} {state.upper()}")
        if missing:
            for path in missing:
                print(f"  - {path.relative_to(ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="show present and missing stage outputs")
    status_parser.add_argument("group", nargs="?", choices=GROUPS, default="all")

    run_parser = subparsers.add_parser("run", help="run a pipeline group")
    run_parser.add_argument("group", choices=GROUPS)
    run_parser.add_argument("--from", dest="from_stage", choices=tuple(STAGE_BY_NAME))
    run_parser.add_argument("--to", dest="to_stage", choices=tuple(STAGE_BY_NAME))
    run_parser.add_argument("--force", action="store_true", help="run selected stages even if outputs exist")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        return print_status(args.group)
    return run_pipeline(args.group, args.from_stage, args.to_stage, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
