from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from models.report import Report
from repositories.user_repository.user_repository import UserRepository


class ReportRepository:
    @staticmethod
    def create(
        db: Session,
        reporter_id: str,
        reported_id: str,
        reason: str,
        details: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Report:
        report = Report(
            reporter_id=reporter_id,
            reported_id=reported_id,
            reason=reason,
            details=details,
            context=context,
            status="pending",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_by_id(db: Session, report_id: str) -> Optional[Report]:
        return db.query(Report).filter(Report.id == report_id).first()

    @staticmethod
    def list_reports(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> List[Dict]:
        query = db.query(Report)
        if status:
            query = query.filter(Report.status == status)

        reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
        items: List[Dict] = []

        for report in reports:
            reporter = UserRepository.get_by_id(db, report.reporter_id)
            reported = UserRepository.get_by_id(db, report.reported_id)
            items.append(
                {
                    **report.to_dict(),
                    "reporter": {
                        "id": reporter.id if reporter else report.reporter_id,
                        "name": reporter.name if reporter else None,
                        "email": reporter.email if reporter else None,
                        "is_admin": reporter.is_admin if reporter else False,
                    },
                    "reported": {
                        "id": reported.id if reported else report.reported_id,
                        "name": reported.name if reported else None,
                        "email": reported.email if reported else None,
                        "is_admin": reported.is_admin if reported else False,
                    },
                }
            )

        return items

    @staticmethod
    def count_reports(db: Session, status: Optional[str] = None) -> int:
        query = db.query(Report)
        if status:
            query = query.filter(Report.status == status)
        return query.count()

    @staticmethod
    def update_status(db: Session, report_id: str, status: str) -> Optional[Report]:
        report = ReportRepository.get_by_id(db, report_id)
        if not report:
            return None

        report.status = status
        db.commit()
        db.refresh(report)
        return report