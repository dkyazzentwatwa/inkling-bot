"""
Project Inkling - Penetration Testing Engagement Manager

Manages pentest engagements, tracks findings, maintains activity logs,
and generates professional reports.

Ensures all testing is authorized and within scope.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import ipaddress

logger = logging.getLogger(__name__)


@dataclass
class Engagement:
    """Penetration testing engagement."""
    id: str
    client: str
    scope: List[str]  # CIDR ranges, hostnames
    start_date: str
    end_date: Optional[str]
    authorized_by: str
    rules_of_engagement: str
    status: str  # active, paused, completed
    created_at: str


@dataclass
class Finding:
    """Security vulnerability finding."""
    id: str
    engagement_id: str
    title: str
    severity: str  # critical, high, medium, low, info
    cvss_score: Optional[float]
    cve_id: Optional[str]
    affected_host: str
    affected_service: str
    description: str
    evidence: str
    remediation: str
    discovered_at: str
    status: str  # new, verified, false_positive, remediated


@dataclass
class Activity:
    """Activity log entry."""
    timestamp: str
    engagement_id: str
    tool: str
    command: str
    target: str
    result: str
    in_scope: bool


class EngagementManager:
    """
    Manages penetration testing engagements.

    Ensures all activities are authorized and within defined scope.
    """

    def __init__(self, data_dir: str = "~/.inkling/pentest"):
        """Initialize engagement manager."""
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.engagements_file = self.data_dir / "engagements.json"
        self.findings_file = self.data_dir / "findings.json"
        self.activity_log_file = self.data_dir / "activity.jsonl"

        self.engagements: Dict[str, Engagement] = self._load_engagements()
        self.findings: Dict[str, Finding] = self._load_findings()

    # ========================================
    # Engagement Management
    # ========================================

    def create_engagement(
        self,
        client: str,
        scope: List[str],
        start_date: str,
        end_date: Optional[str],
        authorized_by: str,
        rules: str
    ) -> Engagement:
        """
        Create new penetration testing engagement.

        Args:
            client: Client name
            scope: List of authorized targets (CIDR ranges, hostnames)
            start_date: Start date (ISO format)
            end_date: End date (ISO format, optional)
            authorized_by: Name and email of authorizer
            rules: Rules of engagement (e.g., "No DoS, no data deletion")

        Returns:
            Created engagement
        """
        import uuid

        engagement_id = str(uuid.uuid4())[:8]

        engagement = Engagement(
            id=engagement_id,
            client=client,
            scope=scope,
            start_date=start_date,
            end_date=end_date,
            authorized_by=authorized_by,
            rules_of_engagement=rules,
            status="active",
            created_at=datetime.now().isoformat()
        )

        self.engagements[engagement_id] = engagement
        self._save_engagements()

        logger.info(f"Created engagement {engagement_id} for {client}")

        return engagement

    def get_active_engagement(self) -> Optional[Engagement]:
        """Get the currently active engagement."""
        active = [e for e in self.engagements.values() if e.status == "active"]
        return active[0] if active else None

    def complete_engagement(self, engagement_id: str) -> bool:
        """Mark engagement as completed."""
        if engagement_id in self.engagements:
            self.engagements[engagement_id].status = "completed"
            self.engagements[engagement_id].end_date = datetime.now().isoformat()
            self._save_engagements()
            return True
        return False

    # ========================================
    # Scope Validation
    # ========================================

    def check_scope(self, target: str) -> Tuple[bool, Optional[str]]:
        """
        Check if target is within authorized scope.

        Args:
            target: IP address or hostname

        Returns:
            Tuple of (in_scope, engagement_id)
        """
        active = self.get_active_engagement()
        if not active:
            logger.warning("No active engagement - target check failed")
            return False, None

        # Try IP validation
        try:
            target_ip = ipaddress.ip_address(target)

            for scope_entry in active.scope:
                try:
                    # Check CIDR range
                    if "/" in scope_entry:
                        network = ipaddress.ip_network(scope_entry, strict=False)
                        if target_ip in network:
                            return True, active.id

                    # Check exact IP
                    elif ipaddress.ip_address(scope_entry) == target_ip:
                        return True, active.id

                except ValueError:
                    continue

        except ValueError:
            # Not an IP, try hostname matching
            for scope_entry in active.scope:
                if target.lower() == scope_entry.lower():
                    return True, active.id
                # Wildcard subdomain matching
                if scope_entry.startswith("*.") and target.lower().endswith(scope_entry[1:].lower()):
                    return True, active.id

        logger.warning(f"Target {target} NOT in scope")
        return False, None

    # ========================================
    # Findings Management
    # ========================================

    def add_finding(
        self,
        engagement_id: str,
        title: str,
        severity: str,
        affected_host: str,
        affected_service: str,
        description: str,
        evidence: str = "",
        remediation: str = "",
        cvss_score: Optional[float] = None,
        cve_id: Optional[str] = None
    ) -> Finding:
        """
        Add a security finding.

        Args:
            engagement_id: Associated engagement ID
            title: Finding title (e.g., "MS17-010 EternalBlue")
            severity: critical, high, medium, low, info
            affected_host: Target host/IP
            affected_service: Service name/port
            description: Detailed description
            evidence: Evidence/proof
            remediation: Remediation advice
            cvss_score: CVSS score (0.0-10.0)
            cve_id: CVE identifier

        Returns:
            Created finding
        """
        import uuid

        finding_id = str(uuid.uuid4())[:8]

        finding = Finding(
            id=finding_id,
            engagement_id=engagement_id,
            title=title,
            severity=severity.lower(),
            cvss_score=cvss_score,
            cve_id=cve_id,
            affected_host=affected_host,
            affected_service=affected_service,
            description=description,
            evidence=evidence,
            remediation=remediation,
            discovered_at=datetime.now().isoformat(),
            status="new"
        )

        self.findings[finding_id] = finding
        self._save_findings()

        logger.info(f"Added {severity} finding: {title}")

        return finding

    def get_findings_by_severity(self, engagement_id: str) -> Dict[str, int]:
        """Get finding count by severity for an engagement."""
        findings = [f for f in self.findings.values() if f.engagement_id == engagement_id]

        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }

        for finding in findings:
            if finding.severity in counts:
                counts[finding.severity] += 1

        return counts

    # ========================================
    # Activity Logging
    # ========================================

    def log_activity(
        self,
        tool: str,
        command: str,
        target: str,
        result: str
    ) -> None:
        """
        Log penetration testing activity.

        All activities are logged for accountability and reporting.

        Args:
            tool: Tool name (nmap, metasploit, hydra, etc.)
            command: Command executed
            target: Target host/IP
            result: Result summary
        """
        in_scope, engagement_id = self.check_scope(target)

        activity = Activity(
            timestamp=datetime.now().isoformat(),
            engagement_id=engagement_id or "none",
            tool=tool,
            command=command,
            target=target,
            result=result,
            in_scope=in_scope
        )

        # Append to activity log (JSONL format)
        with open(self.activity_log_file, 'a') as f:
            f.write(json.dumps(asdict(activity)) + "\n")

        if not in_scope:
            logger.error(f"OUT OF SCOPE ACTIVITY: {tool} against {target}")

    def get_recent_activities(self, limit: int = 50) -> List[Activity]:
        """Get recent activity log entries."""
        if not self.activity_log_file.exists():
            return []

        activities = []
        with open(self.activity_log_file, 'r') as f:
            lines = f.readlines()

        for line in lines[-limit:]:
            try:
                data = json.loads(line)
                activities.append(Activity(**data))
            except Exception as e:
                logger.warning(f"Failed to parse activity: {e}")

        return activities

    # ========================================
    # Reporting
    # ========================================

    def generate_report(
        self,
        engagement_id: str,
        format: str = "markdown"
    ) -> str:
        """
        Generate engagement report.

        Args:
            engagement_id: Engagement ID
            format: Report format (markdown, json, html)

        Returns:
            Report content as string
        """
        engagement = self.engagements.get(engagement_id)
        if not engagement:
            return "Engagement not found"

        findings = [f for f in self.findings.values() if f.engagement_id == engagement_id]
        severity_counts = self.get_findings_by_severity(engagement_id)

        if format == "markdown":
            return self._generate_markdown_report(engagement, findings, severity_counts)
        elif format == "json":
            return json.dumps({
                "engagement": asdict(engagement),
                "findings": [asdict(f) for f in findings],
                "summary": severity_counts
            }, indent=2)
        else:
            return "Unsupported format"

    def _generate_markdown_report(
        self,
        engagement: Engagement,
        findings: List[Finding],
        severity_counts: Dict[str, int]
    ) -> str:
        """Generate markdown format report."""
        report = f"# Penetration Test Report\n\n"
        report += f"## Engagement Information\n\n"
        report += f"- **Client:** {engagement.client}\n"
        report += f"- **Engagement ID:** {engagement.id}\n"
        report += f"- **Start Date:** {engagement.start_date}\n"
        report += f"- **End Date:** {engagement.end_date or 'In Progress'}\n"
        report += f"- **Authorized By:** {engagement.authorized_by}\n"
        report += f"- **Rules of Engagement:** {engagement.rules_of_engagement}\n\n"

        report += f"## Executive Summary\n\n"
        report += f"This report details the findings from the authorized penetration test conducted for {engagement.client}.\n\n"
        report += f"### Scope\n\n"
        for scope_entry in engagement.scope:
            report += f"- {scope_entry}\n"
        report += "\n"

        report += f"### Findings Summary\n\n"
        report += f"| Severity | Count |\n"
        report += f"|----------|-------|\n"
        report += f"| 🔴 Critical | {severity_counts['critical']} |\n"
        report += f"| 🟠 High | {severity_counts['high']} |\n"
        report += f"| 🟡 Medium | {severity_counts['medium']} |\n"
        report += f"| 🟢 Low | {severity_counts['low']} |\n"
        report += f"| ℹ️  Info | {severity_counts['info']} |\n\n"

        report += f"## Detailed Findings\n\n"

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity, 5))

        for i, finding in enumerate(sorted_findings, 1):
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "info": "ℹ️"
            }.get(finding.severity, "")

            report += f"### {i}. {severity_emoji} {finding.title}\n\n"
            report += f"- **Severity:** {finding.severity.upper()}\n"
            if finding.cvss_score:
                report += f"- **CVSS Score:** {finding.cvss_score}\n"
            if finding.cve_id:
                report += f"- **CVE:** {finding.cve_id}\n"
            report += f"- **Affected Host:** {finding.affected_host}\n"
            report += f"- **Affected Service:** {finding.affected_service}\n"
            report += f"- **Status:** {finding.status}\n\n"

            report += f"**Description:**\n\n{finding.description}\n\n"

            if finding.evidence:
                report += f"**Evidence:**\n\n```\n{finding.evidence}\n```\n\n"

            if finding.remediation:
                report += f"**Remediation:**\n\n{finding.remediation}\n\n"

            report += "---\n\n"

        report += f"## Conclusion\n\n"
        report += f"This penetration test identified {len(findings)} security findings. "
        report += f"Immediate attention should be given to {severity_counts['critical']} critical "
        report += f"and {severity_counts['high']} high severity issues.\n\n"

        report += f"*Report generated: {datetime.now().isoformat()}*\n"

        return report

    # ========================================
    # Persistence
    # ========================================

    def _load_engagements(self) -> Dict[str, Engagement]:
        """Load engagements from file."""
        if not self.engagements_file.exists():
            return {}

        try:
            with open(self.engagements_file, 'r') as f:
                data = json.load(f)
            return {k: Engagement(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load engagements: {e}")
            return {}

    def _save_engagements(self) -> None:
        """Save engagements to file."""
        try:
            with open(self.engagements_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.engagements.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save engagements: {e}")

    def _load_findings(self) -> Dict[str, Finding]:
        """Load findings from file."""
        if not self.findings_file.exists():
            return {}

        try:
            with open(self.findings_file, 'r') as f:
                data = json.load(f)
            return {k: Finding(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load findings: {e}")
            return {}

    def _save_findings(self) -> None:
        """Save findings to file."""
        try:
            with open(self.findings_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.findings.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save findings: {e}")
