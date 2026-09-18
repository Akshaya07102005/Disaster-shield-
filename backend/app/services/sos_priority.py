from datetime import datetime

def calculate_sos_priority(sos_request):
    """
    Priority Scoring Algorithm for SOS requests:
    priority_score = (people_affected * 2) + (medical_need_score) + (area_risk_score * 10) + (time_elapsed_minutes * 0.1)
    """
    # 1. Base score from number of affected people
    people_score = (sos_request.people_affected or 1) * 2.0
    
    # 2. Medical needs parsing/severity
    medical_score = 0.0
    med_needs = (sos_request.medical_needs or "").lower()
    desc = (sos_request.description or "").lower()
    
    # Check for severe conditions
    critical_keywords = ['insulin', 'heart', 'oxygen', 'bleeding', 'fracture', 'unconscious', 'injury', 'stroke', 'choking']
    moderate_keywords = ['fever', 'pain', 'elderly', 'pregnant', 'baby', 'child', 'disabled', 'medicine', 'prescription']
    
    if any(k in med_needs or k in desc for k in critical_keywords):
        medical_score = 15.0
    elif any(k in med_needs or k in desc for k in moderate_keywords):
        medical_score = 8.0
    elif med_needs.strip():
        medical_score = 4.0
        
    # 3. Area risk score influence
    # If area is associated, use its current risk score (0.0 to 1.0)
    area_score = 0.0
    if sos_request.area:
        area_score = (sos_request.area.risk_score or 0.0) * 10.0
        
    # 4. Time elapsed score
    # More time elapsed = higher priority
    time_score = 0.0
    if sos_request.created_at:
        elapsed = datetime.utcnow() - sos_request.created_at
        minutes = elapsed.total_seconds() / 60.0
        time_score = minutes * 0.1  # 1 point per 10 minutes elapsed
        
    total_priority = people_score + medical_score + area_score + time_score
    return round(total_priority, 2)
