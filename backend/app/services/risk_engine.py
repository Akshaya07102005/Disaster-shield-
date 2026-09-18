from backend.app.models.core import db, Area, SosRequest

def calculate_area_risk_score(area):
    """
    Computes area-level risk score based on:
    - Elevation (low = high risk)
    - Proximity to water (close = high risk)
    - Population density (high = high risk)
    - Historical disaster index (0.0 to 1.0)
    - Current rainfall intensity (mm/hr)
    - Active SOS request density in the area
    """
    # 1. Historical frequency (0.0 to 1.0)
    hist_freq = area.hist_frequency or 0.0
    
    # 2. Elevation: lower elevation = higher risk. Max elevation 15m.
    elev = area.elevation or 10.0
    elev_factor = max(0.0, min(1.0, (15.0 - elev) / 15.0))
    
    # 3. Water body proximity: closer = higher risk. Max distance 1500m.
    water_dist = area.water_distance or 1000.0
    water_factor = max(0.0, min(1.0, (1500.0 - water_dist) / 1500.0))
    
    # 4. Population density factor: population density per area (max 20000)
    pop_density = area.population or 0
    pop_factor = max(0.0, min(1.0, pop_density / 20000.0))
    
    # 5. Current rainfall factor: max 100mm/hr
    rainfall = area.rainfall_intensity or 0.0
    rain_factor = max(0.0, min(1.0, rainfall / 100.0))
    
    # 6. Active SOS request density factor:
    # Count of active SOS requests in this area
    active_sos = SosRequest.query.filter(
        SosRequest.area_id == area.id,
        SosRequest.status.in_(['pending', 'assigned', 'in-progress'])
    ).count()
    sos_factor = max(0.0, min(1.0, active_sos / 5.0))
    
    # Weights (must sum to 1.0)
    w_hist = 0.25
    w_elev = 0.20
    w_pop = 0.15
    w_water = 0.15
    w_rain = 0.15
    w_sos = 0.10
    
    score = (w_hist * hist_freq + 
             w_elev * elev_factor + 
             w_pop * pop_factor + 
             w_water * water_factor + 
             w_rain * rain_factor + 
             w_sos * sos_factor)
             
    score = min(1.0, max(0.0, score))
    return score

def get_risk_classification(score):
    if score < 0.25:
        return 'Low'
    elif score < 0.50:
        return 'Medium'
    elif score < 0.75:
        return 'High'
    else:
        return 'Critical'

def update_area_risk(area_id):
    """
    Recalculates and updates the risk score and risk level of a single area.
    """
    area = Area.query.get(area_id)
    if not area:
        return None
        
    score = calculate_area_risk_score(area)
    level = get_risk_classification(score)
    
    area.risk_score = score
    area.risk_level = level
    db.session.commit()
    
    # Update boundary_geojson property as well
    import json
    if area.boundary_geojson:
        try:
            geojson = json.loads(area.boundary_geojson)
            if 'properties' in geojson:
                geojson['properties']['risk_score'] = round(score, 4)
                geojson['properties']['risk_level'] = level
                area.boundary_geojson = json.dumps(geojson)
                db.session.commit()
        except Exception:
            pass
            
    return area

def update_all_areas_risk():
    """
    Recalculates and updates all areas in the database.
    """
    areas = Area.query.all()
    updated = []
    for area in areas:
        score = calculate_area_risk_score(area)
        level = get_risk_classification(score)
        area.risk_score = score
        area.risk_level = level
        
        import json
        if area.boundary_geojson:
            try:
                geojson = json.loads(area.boundary_geojson)
                if 'properties' in geojson:
                    geojson['properties']['risk_score'] = round(score, 4)
                    geojson['properties']['risk_level'] = level
                    area.boundary_geojson = json.dumps(geojson)
            except Exception:
                pass
        updated.append(area)
        
    db.session.commit()
    return len(updated)
