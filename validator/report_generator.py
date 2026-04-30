from validator.rig_checker import ValidationReport


def format_validation_report(report: ValidationReport) -> str:
    status_icon = "PASS" if report.is_valid else "FAIL"
    lines = [
        f"File: {report.file_path}",
        f"Overall Status: {status_icon}",
        "",
        report.summary,
        "",
        "Checks:",
    ]

    for check_name, result in report.checks.items():
        check_status = "PASS" if result.get("passed") else "FAIL"
        lines.append(f"- {check_name.title()}: {check_status}")
        for detail in result.get("details", []):
            lines.append(f"  - {detail}")

    if report.warnings:
        lines.extend(["", "Warnings:"])
        for warning in sorted(set(report.warnings)):
            lines.append(f"- {warning}")

    if report.missing_dependencies:
        lines.extend(["", "Missing Dependencies:"])
        for dependency in report.missing_dependencies:
            lines.append(f"- {dependency}")

    if report.errors:
        lines.extend(["", "Failed Checks:"])
        for error in report.errors:
            lines.append(f"- {error}")

    return "\n".join(lines)


def validation_report_to_dict(report: ValidationReport) -> dict:
    return {
        "file_path": report.file_path,
        "is_valid": report.is_valid,
        "summary": report.summary,
        "blocked_by_environment": report.blocked_by_environment,
        "checks": report.checks,
        "warnings": report.warnings,
        "errors": report.errors,
        "missing_dependencies": report.missing_dependencies,
    }
