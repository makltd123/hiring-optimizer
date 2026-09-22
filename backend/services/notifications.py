import hashlib
import hmac
import json
import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from config import settings
from models.models import Project, OptimizationResult, WebhookLog

logger = logging.getLogger(__name__)


async def _send_webhook(url: str, payload: dict, secret: str | None, db: Session, org_id: int | None = None):
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload)
    if secret:
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-HiringOptimizer-Signature"] = f"sha256={sig}"

    status_code = None
    response_body = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, content=body, headers=headers)
            status_code = r.status_code
            response_body = r.text[:1000]
    except Exception as e:
        response_body = str(e)

    log = WebhookLog(
        org_id=org_id,
        event=payload.get("event", "unknown"),
        payload=payload,
        status_code=status_code,
        response_body=response_body,
        sent_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()


async def _send_telegram(chat_id: str, text: str):
    if not settings.telegram_bot_token:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


async def _send_email(to: str, subject: str, body_text: str):
    if not settings.smtp_host:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body_text, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_pass)
            smtp.send_message(msg)
    except Exception as e:
        logger.warning(f"Email send failed to {to}: {e}")


async def send_optimization_complete(
    project: Project,
    result: OptimizationResult,
    db: Session,
):
    from models.models import User, Organization
    # Уведомляем владельца проекта
    owner = db.query(User).filter(User.id == project.user_id).first()
    if not owner:
        return

    coverage_pct = f"{(result.coverage or 0) * 100:.0f}%"
    total_cost = f"{result.total_cost:,.0f} ₽" if result.total_cost else "—"

    if owner.notify_email and owner.email:
        await _send_email(
            to=owner.email,
            subject=f"Оптимизация завершена: {project.title}",
            body_text=(
                f"Оптимизация проекта «{project.title}» завершена.\n\n"
                f"Покрытие команды: {coverage_pct}\n"
                f"Суммарный ФОТ: {total_cost}\n\n"
                f"Результат: http://localhost:3000/project/{project.id}"
            ),
        )

    if owner.telegram_chat_id:
        await _send_telegram(
            chat_id=owner.telegram_chat_id,
            text=(
                f"✅ Оптимизация завершена: <b>{project.title}</b>\n"
                f"Покрытие: {coverage_pct} | ФОТ: {total_cost}"
            ),
        )

    # Вебхук организации
    if project.org_id:
        org = db.query(Organization).filter(Organization.id == project.org_id).first()
        if org and org.webhook_url:
            await _send_webhook(
                url=org.webhook_url,
                payload={
                    "event": "optimization.completed",
                    "project_id": project.id,
                    "project_title": project.title,
                    "coverage": result.coverage,
                    "total_cost": result.total_cost,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                secret=org.webhook_secret,
                db=db,
                org_id=org.id,
            )


async def send_approval_notification(
    to_user_id: int,
    project_title: str,
    event: str,
    comment: str | None,
    db: Session,
):
    from models.models import User
    user = db.query(User).filter(User.id == to_user_id).first()
    if not user:
        return

    messages = {
        "approval_requested": f"Результат оптимизации «{project_title}» ожидает вашего согласования.",
        "approved": f"Результат оптимизации «{project_title}» согласован.",
        "rejected": f"Результат оптимизации «{project_title}» отклонён.",
        "revision": f"Результат оптимизации «{project_title}» отправлен на доработку.",
    }
    text = messages.get(event, f"Событие {event} по проекту «{project_title}»")
    if comment:
        text += f"\n\nКомментарий: {comment}"

    if user.notify_email and user.email:
        await _send_email(to=user.email, subject=text[:80], body_text=text)
    if user.telegram_chat_id:
        await _send_telegram(chat_id=user.telegram_chat_id, text=text)
