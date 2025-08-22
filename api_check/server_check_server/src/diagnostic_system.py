import os
import platform
import json
from typing import Dict, List, Any, Tuple
from enum import Enum
from datetime import datetime
import re

class IssueLevel(Enum):
    """Issue severity levels"""
    GREEN = "green"      # User can fix
    YELLOW = "yellow"    # Needs cooperation
    RED = "red"          # Only server admin

class IssueCategory(Enum):
    """Categories of issues"""
    NETWORK = "network"
    CORS = "cors"
    AUTH = "auth"
    SERVER = "server"
    DATABASE = "database"
    PERMISSION = "permission"
    CONFIGURATION = "config"
    DEPENDENCY = "dependency"
    SSL = "ssl"
    FIREWALL = "firewall"

class DiagnosticSystem:
    """Comprehensive diagnostic system for API issues"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.issue_patterns = self._load_issue_patterns()
        self.command_templates = self._load_command_templates()
    
    def _load_issue_patterns(self) -> Dict[str, Any]:
        """Load patterns for identifying different types of issues"""
        return {
            "cors": {
                "patterns": [
                    r"CORS policy",
                    r"Access-Control-Allow-Origin",
                    r"Cross-Origin Request Blocked",
                    r"No 'Access-Control-Allow-Origin' header"
                ],
                "category": IssueCategory.CORS,
                "level": IssueLevel.YELLOW
            },
            "network_timeout": {
                "patterns": [
                    r"ETIMEDOUT",
                    r"ECONNREFUSED",
                    r"network timeout",
                    r"connect ETIMEDOUT"
                ],
                "category": IssueCategory.NETWORK,
                "level": IssueLevel.GREEN
            },
            "ssl_certificate": {
                "patterns": [
                    r"SSL certificate problem",
                    r"certificate verify failed",
                    r"CERT_HAS_EXPIRED",
                    r"SSL_ERROR"
                ],
                "category": IssueCategory.SSL,
                "level": IssueLevel.RED
            },
            "auth_failed": {
                "patterns": [
                    r"401 Unauthorized",
                    r"403 Forbidden",
                    r"Authentication failed",
                    r"Invalid token"
                ],
                "category": IssueCategory.AUTH,
                "level": IssueLevel.YELLOW
            },
            "server_error": {
                "patterns": [
                    r"500 Internal Server Error",
                    r"502 Bad Gateway",
                    r"503 Service Unavailable",
                    r"504 Gateway Timeout"
                ],
                "category": IssueCategory.SERVER,
                "level": IssueLevel.RED
            },
            "database_error": {
                "patterns": [
                    r"OperationalError",
                    r"connection to database failed",
                    r"too many connections",
                    r"database is locked"
                ],
                "category": IssueCategory.DATABASE,
                "level": IssueLevel.RED
            },
            "permission_denied": {
                "patterns": [
                    r"Permission denied",
                    r"Access denied",
                    r"Insufficient privileges"
                ],
                "category": IssueCategory.PERMISSION,
                "level": IssueLevel.YELLOW
            },
            "missing_dependency": {
                "patterns": [
                    r"ModuleNotFoundError",
                    r"Cannot find module",
                    r"No module named",
                    r"package not found"
                ],
                "category": IssueCategory.DEPENDENCY,
                "level": IssueLevel.GREEN
            }
        }
    
    def _load_command_templates(self) -> Dict[str, Any]:
        """Load command templates for different OS and issues"""
        return {
            "network_diagnostics": {
                "windows": {
                    "desktop": [
                        {
                            "cmd": "ping {host}",
                            "desc": "بررسی اتصال به سرور",
                            "powershell": True
                        },
                        {
                            "cmd": "nslookup {host}",
                            "desc": "بررسی DNS",
                            "powershell": True
                        },
                        {
                            "cmd": "tracert {host}",
                            "desc": "مسیریابی به سرور",
                            "powershell": True
                        },
                        {
                            "cmd": 'Invoke-WebRequest -Uri "https://{host}" -Method HEAD',
                            "desc": "تست HTTPS",
                            "powershell": True
                        }
                    ],
                    "server": [
                        {
                            "cmd": "netstat -an | grep {port}",
                            "desc": "بررسی پورت‌های باز"
                        }
                    ]
                },
                "darwin": {  # macOS
                    "desktop": [
                        {
                            "cmd": "ping -c 4 {host}",
                            "desc": "بررسی اتصال به سرور"
                        },
                        {
                            "cmd": "dig {host}",
                            "desc": "بررسی DNS"
                        },
                        {
                            "cmd": "traceroute {host}",
                            "desc": "مسیریابی به سرور"
                        },
                        {
                            "cmd": "curl -I https://{host}",
                            "desc": "تست HTTPS"
                        }
                    ],
                    "server": [
                        {
                            "cmd": "lsof -i :{port}",
                            "desc": "بررسی پورت‌های باز"
                        }
                    ]
                },
                "linux": {
                    "desktop": [
                        {
                            "cmd": "ping -c 4 {host}",
                            "desc": "بررسی اتصال به سرور"
                        },
                        {
                            "cmd": "host {host}",
                            "desc": "بررسی DNS"
                        },
                        {
                            "cmd": "traceroute {host}",
                            "desc": "مسیریابی به سرور"
                        },
                        {
                            "cmd": "curl -I https://{host}",
                            "desc": "تست HTTPS"
                        }
                    ],
                    "server": [
                        {
                            "cmd": "ss -tuln | grep {port}",
                            "desc": "بررسی پورت‌های باز"
                        },
                        {
                            "cmd": "sudo iptables -L -n | grep {port}",
                            "desc": "بررسی فایروال"
                        }
                    ]
                }
            },
            "cors_diagnostics": {
                "all": {
                    "desktop": [
                        {
                            "cmd": 'curl -X OPTIONS https://{host}/api/v1/{endpoint}/ -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: POST" -v',
                            "desc": "تست CORS headers"
                        },
                        {
                            "cmd": 'curl -X POST https://{host}/api/v1/{endpoint}/ -H "Origin: http://localhost:3000" -d "{}" -v',
                            "desc": "تست POST با Origin"
                        }
                    ],
                    "server": [
                        {
                            "cmd": "docker exec {container} grep -r CORS_ALLOWED_ORIGINS /app/soapify/settings.py",
                            "desc": "بررسی تنظیمات CORS"
                        },
                        {
                            "cmd": "docker exec {container} python manage.py shell -c \"from django.conf import settings; print('CORS_ALLOWED_ORIGINS:', settings.CORS_ALLOWED_ORIGINS)\"",
                            "desc": "نمایش Origins مجاز"
                        },
                        {
                            "cmd": "docker exec {container} python manage.py shell -c \"from django.conf import settings; settings.CORS_ALLOWED_ORIGINS.append('http://localhost:3000'); print('Added localhost:3000')\"",
                            "desc": "اضافه کردن localhost به CORS"
                        }
                    ]
                }
            },
            "auth_diagnostics": {
                "all": {
                    "desktop": [
                        {
                            "cmd": 'curl -X POST https://{host}/api/token/ -d "username=test&password=test" -v',
                            "desc": "تست احراز هویت"
                        },
                        {
                            "cmd": 'curl -H "Authorization: Bearer YOUR_TOKEN" https://{host}/api/v1/{endpoint}/',
                            "desc": "تست با توکن"
                        }
                    ],
                    "server": [
                        {
                            "cmd": "docker exec {container} python manage.py createsuperuser",
                            "desc": "ایجاد کاربر ادمین"
                        },
                        {
                            "cmd": "docker exec {container} python manage.py shell -c \"from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.all())\"",
                            "desc": "لیست کاربران"
                        }
                    ]
                }
            },
            "server_diagnostics": {
                "all": {
                    "desktop": [
                        {
                            "cmd": "curl -I https://{host}/health/",
                            "desc": "بررسی سلامت سرور"
                        }
                    ],
                    "server": [
                        {
                            "cmd": "docker ps -a | grep soapify",
                            "desc": "وضعیت کانتینرها"
                        },
                        {
                            "cmd": "docker logs --tail 50 {container}",
                            "desc": "آخرین لاگ‌ها"
                        },
                        {
                            "cmd": "docker exec {container} python manage.py check",
                            "desc": "بررسی سلامت Django"
                        },
                        {
                            "cmd": "docker restart {container}",
                            "desc": "ری‌استارت سرویس"
                        },
                        {
                            "cmd": "docker-compose -f /path/to/docker-compose.yml restart",
                            "desc": "ری‌استارت کامل"
                        }
                    ]
                }
            },
            "database_diagnostics": {
                "all": {
                    "server": [
                        {
                            "cmd": "docker exec {db_container} mysql -u root -p -e 'SHOW PROCESSLIST;'",
                            "desc": "پردازش‌های فعال MySQL"
                        },
                        {
                            "cmd": "docker exec {container} python manage.py dbshell",
                            "desc": "اتصال به دیتابیس"
                        },
                        {
                            "cmd": "docker exec {container} python manage.py migrate --check",
                            "desc": "بررسی migrations"
                        },
                        {
                            "cmd": "docker exec {container} python manage.py migrate",
                            "desc": "اجرای migrations"
                        }
                    ]
                }
            },
            "ssl_diagnostics": {
                "all": {
                    "desktop": [
                        {
                            "cmd": "openssl s_client -connect {host}:443 -servername {host}",
                            "desc": "بررسی گواهی SSL"
                        },
                        {
                            "cmd": "curl -vI https://{host} 2>&1 | grep -i ssl",
                            "desc": "جزئیات SSL"
                        }
                    ],
                    "server": [
                        {
                            "cmd": "certbot certificates",
                            "desc": "لیست گواهی‌ها"
                        },
                        {
                            "cmd": "nginx -t",
                            "desc": "بررسی تنظیمات Nginx"
                        },
                        {
                            "cmd": "systemctl restart nginx",
                            "desc": "ری‌استارت Nginx"
                        }
                    ]
                }
            },
            "quick_fixes": {
                "all": {
                    "desktop": [
                        {
                            "cmd": "# Windows: Disable CORS in Chrome\nstart chrome.exe --user-data-dir=\"C:/Chrome dev session\" --disable-web-security",
                            "desc": "غیرفعال کردن CORS در Chrome (Windows)"
                        },
                        {
                            "cmd": "# macOS: Disable CORS in Chrome\nopen -n -a /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --args --user-data-dir=\"/tmp/chrome_dev_test\" --disable-web-security",
                            "desc": "غیرفعال کردن CORS در Chrome (macOS)"
                        },
                        {
                            "cmd": "# Use local proxy\nnpx local-cors-proxy --proxyUrl https://{host} --port 8010",
                            "desc": "استفاده از پروکسی محلی"
                        }
                    ]
                }
            }
        }
    
    def diagnose_error(self, error_message: str, error_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Diagnose the error and provide solutions"""
        diagnosis = {
            "error_message": error_message,
            "detected_issues": [],
            "primary_issue": None,
            "solutions": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Detect issues based on patterns
        for issue_key, issue_data in self.issue_patterns.items():
            for pattern in issue_data["patterns"]:
                if re.search(pattern, error_message, re.IGNORECASE):
                    issue_info = {
                        "type": issue_key,
                        "category": issue_data["category"].value,
                        "level": issue_data["level"].value,
                        "confidence": 0.9 if pattern in error_message else 0.7
                    }
                    diagnosis["detected_issues"].append(issue_info)
                    break
        
        # Determine primary issue
        if diagnosis["detected_issues"]:
            diagnosis["primary_issue"] = max(
                diagnosis["detected_issues"], 
                key=lambda x: x["confidence"]
            )
            
            # Generate solutions
            diagnosis["solutions"] = self._generate_solutions(
                diagnosis["primary_issue"],
                error_context
            )
        
        return diagnosis
    
    def _generate_solutions(self, issue: Dict[str, Any], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate solutions based on the issue type"""
        solutions = []
        issue_type = issue["type"]
        
        # Get relevant command templates
        if "cors" in issue_type:
            template_key = "cors_diagnostics"
        elif "network" in issue_type:
            template_key = "network_diagnostics"
        elif "auth" in issue_type:
            template_key = "auth_diagnostics"
        elif "server" in issue_type:
            template_key = "server_diagnostics"
        elif "database" in issue_type:
            template_key = "database_diagnostics"
        elif "ssl" in issue_type:
            template_key = "ssl_diagnostics"
        else:
            template_key = "network_diagnostics"
        
        # Get OS-specific commands
        commands = self._get_commands_for_issue(template_key, context)
        
        # Add quick fixes if applicable
        if issue["level"] in [IssueLevel.GREEN.value, IssueLevel.YELLOW.value]:
            quick_fixes = self._get_commands_for_issue("quick_fixes", context)
            if quick_fixes:
                commands["desktop"].extend(quick_fixes.get("desktop", []))
        
        # Create solution structure
        solution = {
            "issue_type": issue_type,
            "level": issue["level"],
            "commands": commands,
            "explanation": self._get_issue_explanation(issue_type),
            "can_user_fix": issue["level"] == IssueLevel.GREEN.value,
            "needs_cooperation": issue["level"] == IssueLevel.YELLOW.value,
            "admin_only": issue["level"] == IssueLevel.RED.value
        }
        
        solutions.append(solution)
        
        return solutions
    
    def _get_commands_for_issue(self, template_key: str, context: Dict[str, Any] = None) -> Dict[str, List[Dict[str, str]]]:
        """Get OS-specific commands for an issue"""
        if context is None:
            context = {}
        
        # Default values
        host = context.get("host", "django-m.chbk.app")
        port = context.get("port", "8000")
        container = context.get("container", "soapify_web")
        db_container = context.get("db_container", "soapify_mysql")
        endpoint = context.get("endpoint", "voice/upload")
        
        commands = {"desktop": [], "server": []}
        
        if template_key in self.command_templates:
            template = self.command_templates[template_key]
            
            # Get OS-specific or universal commands
            os_commands = template.get(self.os_type, template.get("all", {}))
            
            # Process desktop commands
            for cmd_template in os_commands.get("desktop", []):
                cmd = cmd_template["cmd"].format(
                    host=host,
                    port=port,
                    container=container,
                    db_container=db_container,
                    endpoint=endpoint
                )
                commands["desktop"].append({
                    "command": cmd,
                    "description": cmd_template["desc"],
                    "is_powershell": cmd_template.get("powershell", False)
                })
            
            # Process server commands
            for cmd_template in os_commands.get("server", []):
                cmd = cmd_template["cmd"].format(
                    host=host,
                    port=port,
                    container=container,
                    db_container=db_container,
                    endpoint=endpoint
                )
                commands["server"].append({
                    "command": cmd,
                    "description": cmd_template["desc"]
                })
        
        return commands
    
    def _get_issue_explanation(self, issue_type: str) -> str:
        """Get explanation for issue type"""
        explanations = {
            "cors": "مرورگر به دلایل امنیتی از ارسال درخواست به دامنه‌های مختلف جلوگیری می‌کند. سرور باید تنظیمات CORS را اصلاح کند.",
            "network_timeout": "اتصال به سرور برقرار نمی‌شود. ممکن است مشکل از اینترنت شما، فایروال یا سرور باشد.",
            "ssl_certificate": "گواهی SSL سرور منقضی شده یا معتبر نیست. نیاز به تمدید یا نصب گواهی جدید است.",
            "auth_failed": "احراز هویت ناموفق بود. بررسی کنید که توکن یا اطلاعات ورود صحیح باشد.",
            "server_error": "سرور با خطا مواجه شده. ممکن است مشکل از کد، دیتابیس یا منابع سرور باشد.",
            "database_error": "دیتابیس در دسترس نیست یا پر شده. نیاز به بررسی و رفع مشکل دیتابیس است.",
            "permission_denied": "دسترسی به این منبع مجاز نیست. نیاز به تنظیم مجوزها است.",
            "missing_dependency": "یک پکیج یا کتابخانه مورد نیاز نصب نیست."
        }
        
        return explanations.get(issue_type, "خطای ناشناخته. نیاز به بررسی بیشتر.")
    
    def generate_test_sequence(self, api_endpoint: str, issue_type: str = None) -> List[Dict[str, Any]]:
        """Generate a complete test sequence for an API endpoint"""
        sequence = []
        
        # Basic connectivity test
        sequence.append({
            "step": 1,
            "level": "desktop",
            "command": f"ping -c 1 django-m.chbk.app" if self.os_type != "windows" else "ping -n 1 django-m.chbk.app",
            "description": "بررسی اتصال پایه به سرور",
            "expected": "Reply from server",
            "on_failure": "Check internet connection"
        })
        
        # HTTPS test
        sequence.append({
            "step": 2,
            "level": "desktop",
            "command": f"curl -I https://django-m.chbk.app",
            "description": "بررسی دسترسی HTTPS",
            "expected": "HTTP/2 200 or HTTP/1.1 200",
            "on_failure": "Check firewall or proxy settings"
        })
        
        # API endpoint test
        sequence.append({
            "step": 3,
            "level": "desktop",
            "command": f"curl -X GET https://django-m.chbk.app/api/v1/{api_endpoint}/",
            "description": f"تست GET endpoint: {api_endpoint}",
            "expected": "JSON response",
            "on_failure": "Check API is running"
        })
        
        # If POST endpoint, test OPTIONS for CORS
        if api_endpoint in ["voice/upload", "stt/transcribe", "checklists"]:
            sequence.append({
                "step": 4,
                "level": "desktop",
                "command": f'curl -X OPTIONS https://django-m.chbk.app/api/v1/{api_endpoint}/ -H "Origin: http://localhost:3000" -v',
                "description": "بررسی CORS preflight",
                "expected": "Access-Control-Allow-Origin header",
                "on_failure": "CORS not configured"
            })
        
        # Server-side checks
        sequence.append({
            "step": 5,
            "level": "server",
            "command": "docker ps | grep soapify",
            "description": "بررسی وضعیت containers",
            "expected": "All containers running",
            "on_failure": "Restart containers"
        })
        
        sequence.append({
            "step": 6,
            "level": "server",
            "command": "docker logs --tail 20 soapify_web | grep ERROR",
            "description": "بررسی خطاهای اخیر",
            "expected": "No recent errors",
            "on_failure": "Check error details"
        })
        
        return sequence
    
    def generate_fix_script(self, issue_type: str, os_type: str = None) -> str:
        """Generate a complete fix script for common issues"""
        if os_type is None:
            os_type = self.os_type
        
        scripts = {
            "cors": {
                "windows": """# CORS Fix Script for Windows
# Run in PowerShell as Administrator

Write-Host "Starting CORS fix process..." -ForegroundColor Green

# Test current CORS status
Write-Host "`nTesting current CORS configuration..." -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "https://django-m.chbk.app/api/v1/voice/upload/" -Method OPTIONS -Headers @{
    "Origin" = "http://localhost:3000"
    "Access-Control-Request-Method" = "POST"
} -UseBasicParsing

if ($response.Headers["Access-Control-Allow-Origin"]) {
    Write-Host "CORS is already configured!" -ForegroundColor Green
} else {
    Write-Host "CORS not configured. Please run these commands on server:" -ForegroundColor Red
    Write-Host @"
docker exec soapify_web python manage.py shell << EOF
from django.conf import settings
origins = list(settings.CORS_ALLOWED_ORIGINS)
origins.append('http://localhost:3000')
print(f'Updated CORS origins: {origins}')
EOF
"@
}

# Alternative: Use Chrome without CORS
Write-Host "`nAlternative: Launch Chrome without CORS checks" -ForegroundColor Yellow
$chromePath = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
if (Test-Path $chromePath) {
    Start-Process $chromePath -ArgumentList '--disable-web-security', '--user-data-dir="C:\temp\chrome_test"', 'http://localhost:3000'
}
""",
                "darwin": """#!/bin/bash
# CORS Fix Script for macOS

echo "Starting CORS fix process..."

# Test current CORS status
echo -e "\nTesting current CORS configuration..."
response=$(curl -s -I -X OPTIONS https://django-m.chbk.app/api/v1/voice/upload/ \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST")

if echo "$response" | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ CORS is already configured!"
else
    echo "❌ CORS not configured. Please run these commands on server:"
    cat << 'EOF'
docker exec soapify_web python manage.py shell << END
from django.conf import settings
origins = list(settings.CORS_ALLOWED_ORIGINS)
origins.append('http://localhost:3000')
print(f'Updated CORS origins: {origins}')
END
EOF
fi

# Alternative: Use Chrome without CORS
echo -e "\nAlternative: Launch Chrome without CORS checks"
open -n -a /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --args --disable-web-security --user-data-dir="/tmp/chrome_test" http://localhost:3000
"""
            },
            "network": {
                "all": """#!/bin/bash
# Network Diagnostic Script

echo "Running network diagnostics..."

# Function to check connectivity
check_connection() {
    local host=$1
    echo -n "Checking $host... "
    if ping -c 1 $host > /dev/null 2>&1; then
        echo "✅ OK"
        return 0
    else
        echo "❌ Failed"
        return 1
    fi
}

# Check various endpoints
check_connection "8.8.8.8"  # Google DNS
check_connection "django-m.chbk.app"  # Your server

# DNS lookup
echo -e "\nDNS Resolution:"
nslookup django-m.chbk.app

# Trace route
echo -e "\nRoute to server:"
traceroute -m 10 django-m.chbk.app 2>/dev/null || tracert django-m.chbk.app

# Check ports
echo -e "\nChecking HTTPS port:"
nc -zv django-m.chbk.app 443
"""
            }
        }
        
        return scripts.get(issue_type, {}).get(os_type, scripts.get(issue_type, {}).get("all", "# No specific script available"))
    
    def export_diagnostic_report(self, diagnosis: Dict[str, Any], format: str = "json") -> str:
        """Export diagnostic report in various formats"""
        if format == "json":
            return json.dumps(diagnosis, indent=2, ensure_ascii=False)
        
        elif format == "markdown":
            report = f"""# Diagnostic Report
Generated: {diagnosis['timestamp']}

## Error Message
```
{diagnosis['error_message']}
```

## Detected Issues
"""
            for issue in diagnosis['detected_issues']:
                level_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(issue['level'], "⚪")
                report += f"\n### {level_emoji} {issue['type'].upper()}\n"
                report += f"- Category: {issue['category']}\n"
                report += f"- Confidence: {issue['confidence']*100:.0f}%\n"
                report += f"- Level: {issue['level']}\n"
            
            if diagnosis['solutions']:
                report += "\n## Solutions\n"
                for i, solution in enumerate(diagnosis['solutions'], 1):
                    report += f"\n### Solution {i}: {solution['issue_type']}\n"
                    report += f"{solution['explanation']}\n\n"
                    
                    if solution['commands']['desktop']:
                        report += "#### Desktop Commands:\n"
                        for cmd in solution['commands']['desktop']:
                            report += f"```bash\n# {cmd['description']}\n{cmd['command']}\n```\n"
                    
                    if solution['commands']['server']:
                        report += "#### Server Commands (Need SSH Access):\n"
                        for cmd in solution['commands']['server']:
                            report += f"```bash\n# {cmd['description']}\n{cmd['command']}\n```\n"
            
            return report
        
        elif format == "html":
            # Generate HTML report
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Diagnostic Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .issue {{ margin: 20px 0; padding: 15px; border-radius: 5px; }}
        .green {{ background-color: #d4edda; }}
        .yellow {{ background-color: #fff3cd; }}
        .red {{ background-color: #f8d7da; }}
        pre {{ background-color: #f5f5f5; padding: 10px; overflow-x: auto; }}
        .command {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>Diagnostic Report</h1>
    <p>Generated: {diagnosis['timestamp']}</p>
    <h2>Error Message</h2>
    <pre>{diagnosis['error_message']}</pre>
"""
            # Add issues and solutions...
            html += "</body></html>"
            return html
        
        return str(diagnosis)