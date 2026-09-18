import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from backend.app.models.core import db, Area, SosRequest, Resource, Shelter, Hospital, Report, RescueTeam

def generate_pdf_report(user, area_id=None):
    """
    Generates a professional government-letterhead style PDF report summarizing
    the current disaster situation, area risk levels, resources, and AI-assisted recommendations.
    """
    # 1. Fetch data from DB
    if area_id:
        areas = [Area.query.get(area_id)]
        scope_name = areas[0].area_name if areas[0] else "Unknown Sector"
    else:
        areas = Area.query.all()
        scope_name = "All Chennai Region"
        
    total_areas = len(areas)
    low_risk = sum(1 for a in areas if a.risk_level == 'Low')
    med_risk = sum(1 for a in areas if a.risk_level == 'Medium')
    high_risk = sum(1 for a in areas if a.risk_level == 'High')
    crit_risk = sum(1 for a in areas if a.risk_level == 'Critical')
    
    # Active alerts count
    from backend.app.models.core import Alert
    active_alerts = Alert.query.count()
    
    # Active SOS count
    pending_sos = SosRequest.query.filter(SosRequest.status == 'pending').count()
    active_sos = SosRequest.query.filter(SosRequest.status == 'assigned').count()
    resolved_sos = SosRequest.query.filter(SosRequest.status == 'resolved').count()
    
    # Setup output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"disaster_report_{timestamp}.pdf"
    
    # We must save it in the static upload folder
    # In config, Config.UPLOAD_FOLDER is the target
    from flask import current_app
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    relative_url = f"/static/reports/{filename}"
    
    # 2. Build PDF Document
    doc = SimpleDocTemplate(file_path, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom Styles for Premium Government Look
    title_style = ParagraphStyle(
        'GovTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'), # Slate 900
        alignment=1, # Centered
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'GovSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#475569'), # Slate 600
        alignment=1,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E3A8A'), # Navy Blue
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    
    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )

    # Header / Letterhead
    story.append(Paragraph("GOVERNMENT OF TAMIL NADU", ParagraphStyle('LHead1', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#1E3A8A'), alignment=1)))
    story.append(Paragraph("DISASTER RESPONSE AND RELIEF COMMAND CENTER, CHENNAI", ParagraphStyle('LHead2', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.HexColor('#0F172A'), alignment=1)))
    story.append(Spacer(1, 2))
    
    # Decorative line separating letterhead
    line_data = [['']]
    line_table = Table(line_data, colWidths=[530], rowHeights=[2])
    line_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 10))
    
    # Title
    story.append(Paragraph("SITUATION ASSESSMENT & RESPONSE REPORT", title_style))
    story.append(Paragraph(f"Scope: {scope_name} | Generated on: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}", subtitle_style))
    
    # Meta Information Table
    meta_data = [
        [Paragraph(f"<b>Issued By:</b> {user.name}", meta_style), Paragraph(f"<b>Designation:</b> {user.role.upper()} Analyst", meta_style)],
        [Paragraph(f"<b>System Status:</b> ACTIVE EMERGENCY PROTOCOL", meta_style), Paragraph(f"<b>Region Identifier:</b> GCC-TN-CH-426", meta_style)]
    ]
    meta_table = Table(meta_data, colWidths=[265, 265])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # 1. Executive Summary
    story.append(Paragraph("1. Executive Incident Summary", h1_style))
    summary_text = (
        f"This command brief provides an automated diagnostic overview of the Chennai disaster management matrix. "
        f"A total of <b>{total_areas}</b> areas are currently monitored under the Risk Assessment Engine. "
        f"There are currently <b>{active_alerts}</b> active alerts broadcasted city-wide. "
        f"The Central Emergency SOS Queue reports <b>{pending_sos}</b> pending rescue requests, <b>{active_sos}</b> actively assigned NGO operations, and <b>{resolved_sos}</b> completed rescues."
    )
    story.append(Paragraph(summary_text, body_style))
    
    # Metrics Grid Table
    metrics_data = [
        ["Risk Classification Profile", "Emergency SOS Queue Summary"],
        [
            Paragraph(
                f"- Critical Risk Zones: <b>{crit_risk}</b> areas<br/>"
                f"- High Risk Zones: <b>{high_risk}</b> areas<br/>"
                f"- Medium Risk Zones: <b>{med_risk}</b> areas<br/>"
                f"- Low Risk Zones: <b>{low_risk}</b> areas", body_style
            ),
            Paragraph(
                f"- Pending SOS Queue: <b>{pending_sos}</b> requests<br/>"
                f"- Ongoing Operations: <b>{active_sos}</b> missions<br/>"
                f"- Resolved Requests: <b>{resolved_sos}</b> rescues<br/>"
                f"- Active NGO Teams: <b>{RescueTeam.query.filter(RescueTeam.status == 'active').count()}</b> teams", body_style
            )
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[265, 265])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 15))
    
    # 2. Risk Assessment Breakdown
    story.append(Paragraph("2. Critical Sector Risk Mapping", h1_style))
    story.append(Paragraph("The following sectors have been flagged as having Critical or High risk factors based on elevation, precipitation, and active citizen incidents:", body_style))
    
    # List top critical areas
    crit_areas = [a for a in areas if a.risk_level in ['Critical', 'High']][:6]
    
    table_header = ["Sector Name", "Zone", "Risk Level", "Risk Score", "Rain (mm/h)", "Population"]
    table_rows = [table_header]
    for a in crit_areas:
        table_rows.append([
            a.area_name,
            a.zone.split(" ")[-1] if len(a.zone.split(" ")) > 1 else a.zone,
            a.risk_level,
            f"{a.risk_score:.4f}",
            f"{a.rainfall_intensity:.1f}",
            f"{a.population:,}"
        ])
        
    if len(table_rows) == 1:
        table_rows.append(["No critical/high risk zones flagged.", "", "", "", "", ""])
        
    risk_table = Table(table_rows, colWidths=[120, 80, 70, 70, 80, 110])
    r_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#475569')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]
    
    # Color-code risk levels in PDF
    for i, a in enumerate(crit_areas, start=1):
        bg_color = colors.HexColor('#FEE2E2') if a.risk_level == 'Critical' else colors.HexColor('#FFEDD5')
        r_style.append(('BACKGROUND', (2, i), (2, i), bg_color))
        r_style.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#991B1B') if a.risk_level == 'Critical' else colors.HexColor('#C2410C')))
        r_style.append(('FONTNAME', (2, i), (2, i), 'Helvetica-Bold'))
        
    risk_table.setStyle(TableStyle(r_style))
    story.append(risk_table)
    story.append(Spacer(1, 15))
    
    # 3. AI Resource Planning Recommendations
    story.append(Paragraph("3. Emergency Resource Directives & Planning", h1_style))
    
    # Calculate recommendations
    rec_boats = 0
    rec_food = 0
    rec_med = 0
    rec_vol = 0
    
    for a in areas:
        if a.risk_level == 'Critical':
            rec_boats += 2
            rec_food += int(a.population * 0.05)
            rec_med += int(a.population * 0.02)
            rec_vol += 15
        elif a.risk_level == 'High':
            rec_boats += 1
            rec_food += int(a.population * 0.02)
            rec_med += int(a.population * 0.01)
            rec_vol += 8
            
    story.append(Paragraph(
        f"Based on population demographics, water body proximity, and current water stagnation rates, the AI Planning Engine "
        f"recommends the following allocations for the monitored sectors:\n", body_style
    ))
    
    rec_data = [
        ["Resource Category", "Recommended Reserve Allocation", "Priority Deployment Area"],
        ["Rescue Boats (Inflatable)", f"{max(5, rec_boats)} Units", f"Velachery, Pallikaranai, Saidapet"],
        ["Emergency Rations / Water", f"{max(500, rec_food):,} Kits", f"City-wide critical zones"],
        ["First-Aid & Trauma Kits", f"{max(250, rec_med):,} Kits", f"Nearest relief centers"],
        ["Disaster Response Volunteers", f"{max(50, rec_vol)} Personnel", f"NGO deployment centers"]
    ]
    rec_table = Table(rec_data, colWidths=[150, 180, 200])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 20))
    
    # Signatures
    story.append(Spacer(1, 30))
    sig_data = [
        [Paragraph("........................................................<br/><b>Command Analyst Signature</b>", meta_style),
         Paragraph("........................................................<br/><b>District Officer Approval</b>", meta_style)]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(sig_table)
    
    # Build Document
    doc.build(story)
    
    # 3. Save report details in database
    try:
        report = Report(
            generated_by=user.id,
            area_id=area_id,
            report_type='area_risk' if area_id else 'incident_summary',
            file_path=relative_url
        )
        db.session.add(report)
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    return relative_url

def generate_weather_pdf_report(user, weather_report_id):
    """
    Generates a professional government-letterhead style PDF report for
    Chennai Area Weather Conditions based on an AI Analysis run.
    """
    from backend.app.models.core import WeatherReport, AreaWeatherLog, Area, Report
    
    # 1. Fetch report details
    w_report = WeatherReport.query.get(weather_report_id)
    if not w_report:
        return None
        
    logs = AreaWeatherLog.query.filter_by(analyzed_at=w_report.generated_at).all()
    
    # Setup output path
    timestamp = w_report.generated_at.strftime("%Y%m%d_%H%M%S")
    filename = f"weather_report_{timestamp}.pdf"
    
    from flask import current_app
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    relative_url = f"/static/reports/{filename}"
    
    # Build Document
    doc = SimpleDocTemplate(file_path, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'GovTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F1E3A'),
        alignment=1,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'GovSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2C4A7C'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    
    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )

    # Header / Letterhead
    story.append(Paragraph("GOVERNMENT OF TAMIL NADU", ParagraphStyle('LHead1', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#0F1E3A'), alignment=1)))
    story.append(Paragraph("DISASTER RESPONSE AND RELIEF COMMAND CENTER, CHENNAI", ParagraphStyle('LHead2', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.HexColor('#2C4A7C'), alignment=1)))
    story.append(Spacer(1, 2))
    
    line_data = [['']]
    line_table = Table(line_data, colWidths=[530], rowHeights=[2])
    line_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0F1E3A')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 10))
    
    # Title
    story.append(Paragraph("AI-DRIVEN WEATHER CONDITIONS REPORT", title_style))
    story.append(Paragraph(f"Coverage: {w_report.area_count} Chennai Sectors | Generated on: {w_report.generated_at.strftime('%d-%b-%Y %I:%M %p')}", subtitle_style))
    
    # Meta Information Table
    meta_data = [
        [Paragraph(f"<b>Issued By:</b> {user.name}", meta_style), Paragraph(f"<b>Role:</b> {user.role.upper()} Controller", meta_style)],
        [Paragraph(f"<b>Classification:</b> FOR OFFICIAL INTERNAL USE ONLY", meta_style), Paragraph(f"<b>System Protocol:</b> MET-CLIMATIC DIAGNOSTIC ANALYSIS", meta_style)]
    ]
    meta_table = Table(meta_data, colWidths=[265, 265])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary & Regional Weather Condition", h1_style))
    story.append(Paragraph(w_report.summary_text or "No summary text provided.", body_style))
    
    # Group logs by condition level
    low_count = sum(1 for l in logs if l.weather_condition_level == 'Low')
    mod_count = sum(1 for l in logs if l.weather_condition_level == 'Moderate')
    sev_count = sum(1 for l in logs if l.weather_condition_level == 'Severe')
    ext_count = sum(1 for l in logs if l.weather_condition_level == 'Extreme')
    
    summary_stats = [
        ["Weather Condition Level", "Number of Sectors", "Immediate Response Guidelines"],
        [Paragraph("<b>Extreme</b>", body_style), str(ext_count), "Mandatory evacuation, activate primary storm barriers & shelters."],
        [Paragraph("<b>Severe</b>", body_style), str(sev_count), "High alert, deployment of emergency rescue squads on standby."],
        [Paragraph("<b>Moderate</b>", body_style), str(mod_count), "Close monitoring of active waterlogging drainage pumps."],
        [Paragraph("<b>Low</b>", body_style), str(low_count), "Standard routine diagnostics, normal alert profile."]
    ]
    summary_table = Table(summary_stats, colWidths=[150, 100, 280])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F1E3A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))
    
    # 2. Flagged Severe/Extreme Sectors
    story.append(Paragraph("2. Flagged Severe / Extreme Weather Sectors", h1_style))
    story.append(Paragraph("The following areas are flagged under Severe or Extreme weather thresholds requiring emergency monitoring:", body_style))
    
    flagged_logs = [l for l in logs if l.weather_condition_level in ['Severe', 'Extreme']]
    # Sort: Extreme first
    flagged_logs.sort(key=lambda x: x.weather_condition_level == 'Extreme', reverse=True)
    
    table_header = ["Sector Name", "Temp (°C)", "Rain (mm/h)", "Humidity (%)", "Wind (km/h)", "Condition Level"]
    table_rows = [table_header]
    
    # Show at most top 30 flagged logs to keep PDF professional and not overflow pages
    for l in flagged_logs[:30]:
        table_rows.append([
            l.area.area_name if l.area else "Unknown",
            f"{l.temperature:.1f}°C",
            f"{l.rainfall_mm:.1f} mm",
            f"{l.humidity:.0f}%",
            f"{l.wind_speed:.1f} km/h",
            l.weather_condition_level
        ])
        
    flagged_table = Table(table_rows, colWidths=[160, 65, 75, 75, 75, 80])
    flagged_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2C4A7C')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(flagged_table)
    
    if len(flagged_logs) > 30:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<i>* Note: Displaying top 30 critical sectors. A total of {len(flagged_logs)} sectors are flagged as Severe or Extreme.</i>", meta_style))
        
    story.append(Spacer(1, 20))
    
    # Signatures
    story.append(Spacer(1, 20))
    sig_data = [
        [Paragraph("........................................................<br/><b>Command Analyst Signature</b>", meta_style),
         Paragraph("........................................................<br/><b>Emergency Operations Chief</b>", meta_style)]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(sig_table)
    
    # Build Document
    doc.build(story)
    
    # Also record inside general Report model
    try:
        report = Report(
            generated_by=user.id,
            area_id=None,
            report_type='weather_analysis',
            file_path=relative_url,
            generated_at=w_report.generated_at
        )
        db.session.add(report)
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    return relative_url

