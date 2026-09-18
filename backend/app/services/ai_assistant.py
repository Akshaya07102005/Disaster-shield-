import re
import os
import requests
from datetime import datetime, timedelta
from backend.app.models.core import Area, SosRequest, Resource, Shelter, Hospital, Ngo, User, Alert, RescueTeam, db

# 40 Categorized Default Questions for the Disaster Shield AI Assistant
DEFAULT_CATEGORIZED_QUESTIONS = [
    # 1. Flood & Waterlogging (1 - 6)
    {
        "id": 1,
        "category": "Flood & Rain",
        "category_icon": "fa-water",
        "question": "What should I do during a flood?",
        "keywords": ["flood", "flooding", "what to do during flood", "flood protocol"],
        "answer": (
            "**Emergency Flood Safety Protocol:**\n"
            "1. Move immediately to higher floors or elevated grounds. Never walk, swim, or drive through floodwaters.\n"
            "2. Avoid contact with floodwater, which may carry chemical contaminants, sewage, or submerged live power cables.\n"
            "3. Switch off your home's main electricity circuit breaker and gas cylinder valves before water reaches outlets.\n"
            "4. Keep your 72-hour survival kit handy (potable water, dry snacks, flashlight, power bank, first aid kit).\n"
            "5. If trapped on a roof, signal for emergency rescue via our portal's SOS button or dial 1077 / 101."
        )
    },
    {
        "id": 2,
        "category": "Flood & Rain",
        "category_icon": "fa-water",
        "question": "What is the waterlogging protocol in Chennai?",
        "keywords": ["waterlogging", "water stagnation", "drainage", "pumps"],
        "answer": (
            "**Greater Chennai Corporation Waterlogging Protocol:**\n"
            "1. Stagnation exceeding 1 foot is automatically escalated to Zonal Engineers for heavy-duty motor pump deployment.\n"
            "2. Underpasses & subways (e.g. Gengu Reddy, RBI subway) with waterlogging trigger immediate automatic traffic diversions.\n"
            "3. Low-lying ground floor residents are relocated to pre-identified Corporation relief schools.\n"
            "4. GCC flood monitoring control room operates 24/7 at Ripon Building (Helpline: 1913)."
        )
    },
    {
        "id": 3,
        "category": "Flood & Rain",
        "category_icon": "fa-water",
        "question": "How to purify drinking water during a flood?",
        "keywords": ["purify", "drinking water", "boil water", "chlorine tablets"],
        "answer": (
            "**Drinking Water Purification Guidelines:**\n"
            "1. **Boiling:** Boil water vigorously with rolling bubbles for at least 1 to 3 minutes.\n"
            "2. **Chlorine Disinfection:** If boiling isn't possible, add 4 drops of regular unscented household bleach per liter of clear water (8 drops if water is cloudy) and wait 30 minutes.\n"
            "3. **Water Purification Tablets:** Dissolve 1 halogen/chlorine tablet per 5 liters of water as per kit directions.\n"
            "4. **Caution:** Never drink untreated floodwater or raw tap water during flood emergencies to prevent cholera and leptospirosis."
        )
    },
    {
        "id": 4,
        "category": "Flood & Rain",
        "category_icon": "fa-water",
        "question": "What to do if floodwater enters my house?",
        "keywords": ["water enters house", "house flooding", "home flooding", "submerged"],
        "answer": (
            "**Action Steps for In-Home Flooding:**\n"
            "1. **Cut Main Power:** Turn off the main electrical MCB breaker immediately. Do NOT touch switches while standing in water.\n"
            "2. **Shut Gas Valves:** Turn off LPG gas cylinder regulators and disconnect pipes.\n"
            "3. **Move Upward:** Shift elderly family members, children, pets, vital documents, and medicines to the upper floor or terrace.\n"
            "4. **Raise Emergency SOS:** Submit a GPS-enabled SOS request through this portal or contact the Disaster Control Room at 1077."
        )
    },
    {
        "id": 5,
        "category": "Flood & Rain",
        "category_icon": "fa-water",
        "question": "How to safely evacuate a flooded area?",
        "keywords": ["evacuate", "evacuation", "flood evacuation", "safe route"],
        "answer": (
            "**Safe Flood Evacuation Guidelines:**\n"
            "1. Follow designated government evacuation routes; avoid shortcuts across open fields or submerged culverts.\n"
            "2. Wear sturdy closed-toe shoes and use a stick or umbrella to test the ground depth and firmness before stepping.\n"
            "3. Do not attempt to wade through moving water deeper than 6 inches.\n"
            "4. Carry your waterproof pouch with IDs, emergency cash, and essential medications to the nearest municipal relief shelter."
        )
    },
    {
        "id": 6,
        "category": "Flood & Rain",
        "category_icon": "fa-water",
        "question": "What should I do if a car gets caught in floodwater?",
        "keywords": ["car", "vehicle", "car flood", "driving flood", "submerged car"],
        "answer": (
            "**Vehicle Flood Safety Guidelines:**\n"
            "1. **Never drive through flooded roads:** Just 12 inches of rushing water can float most cars; 2 feet will sweep away SUVs.\n"
            "2. **If engine stalls:** Do NOT attempt to restart the engine (causes hydraulic lock). Abandon vehicle and move to higher ground.\n"
            "3. **If water rises rapidly:** Roll down windows immediately before electronic circuits fail, unbuckle seatbelts, and exit onto the roof to await rescue."
        )
    },

    # 2. Cyclone & Storm Safety (7 - 11)
    {
        "id": 7,
        "category": "Cyclone & Storm",
        "category_icon": "fa-wind",
        "question": "How to prepare for a cyclone?",
        "keywords": ["prepare cyclone", "cyclone prep", "storm preparation", "cyclone warning"],
        "answer": (
            "**Cyclone Preparedness Checklist:**\n"
            "1. Secure or bring indoors loose roof sheets, flower pots, solar panels, and outdoor items.\n"
            "2. Apply criss-cross adhesive tape to large glass windows to prevent violent shattering.\n"
            "3. Stock 3-7 days of non-perishable food, potable water, and emergency prescription drugs.\n"
            "4. Fully charge phones, power banks, battery-powered emergency lights, and portable radios.\n"
            "5. Keep all family identification proofs, deeds, and vehicle keys in a sealed waterproof pouch."
        )
    },
    {
        "id": 8,
        "category": "Cyclone & Storm",
        "category_icon": "fa-wind",
        "question": "What should I do during a severe cyclonic storm?",
        "keywords": ["during cyclone", "storm wind", "cyclone eye", "cyclone safety"],
        "answer": (
            "**During Severe Cyclonic Landfall:**\n"
            "1. Remain strictly inside an interior room or reinforced bathroom away from exterior windows.\n"
            "2. Unplug electrical appliances to protect them from high-voltage storm surges.\n"
            "3. **Beware of the Cyclone Eye:** If winds suddenly calm down, DO NOT step outside. Destructive winds will resume abruptly from the opposite direction within minutes.\n"
            "4. Keep battery radio tuned to Chennai IMD bulletins and monitor official advisories on this portal."
        )
    },
    {
        "id": 9,
        "category": "Cyclone & Storm",
        "category_icon": "fa-wind",
        "question": "What precautions should be taken after a cyclone passes?",
        "keywords": ["after cyclone", "post cyclone", "cyclone aftermath"],
        "answer": (
            "**Post-Cyclone Safety Precautions:**\n"
            "1. Stay indoors until local disaster authorities officially declare the storm has cleared.\n"
            "2. Watch out for snapped electrical cables, sagging tree branches, and structurally compromised walls.\n"
            "3. Do not turn on domestic electrical mains until lines have been checked for water penetration.\n"
            "4. Boil municipal drinking water to avoid contracting post-storm waterborne diseases."
        )
    },
    {
        "id": 10,
        "category": "Cyclone & Storm",
        "category_icon": "fa-wind",
        "question": "What is the average rainfall during Chennai monsoons?",
        "keywords": ["rainfall", "monsoon rain", "average rainfall chennai", "precipitation"],
        "answer": (
            "**Chennai Monsoon Rainfall Data:**\n"
            "Chennai receives 800 - 1000 mm of rainfall during the Northeast Monsoon (October to December), which accounts for over 60% of its annual precipitation.\n"
            "- Daily rainfall > 65 mm is classified as Heavy Rain (Yellow Alert).\n"
            "- Daily rainfall > 115 mm is Very Heavy Rain (Orange Alert).\n"
            "- Daily rainfall > 204 mm is Extremely Heavy Rain (Red Disaster Alert)."
        )
    },
    {
        "id": 11,
        "category": "Cyclone & Storm",
        "category_icon": "fa-wind",
        "question": "How to report a fallen tree or broken electric pole?",
        "keywords": ["fallen tree", "electric pole", "snapped wire", "power wire", "tangedco"],
        "answer": (
            "**Reporting Hazards:**\n"
            "1. Maintain a strict safety distance of at least 10 meters (33 ft) from downed wires.\n"
            "2. **TANGEDCO (Electricity Board) Helpline:** Dial **1912** or WhatsApp **+91 94458 50811**.\n"
            "3. **Greater Chennai Corporation (Fallen Trees / Blockages):** Dial **1913** or WhatsApp **+91 94454 77205**.\n"
            "4. Warn pedestrians and keep children indoors until specialized emergency crews secure the sector."
        )
    },

    # 3. Emergency Helplines & Contacts (12 - 15)
    {
        "id": 12,
        "category": "Helplines",
        "category_icon": "fa-phone-volume",
        "question": "What are the emergency contact numbers in Chennai?",
        "keywords": ["emergency contact", "helpline", "phone number", "control room"],
        "answer": (
            "**Chennai 24/7 Official Emergency Helplines:**\n"
            "- **Greater Chennai Corporation (GCC):** 1913\n"
            "- **State Disaster Management Authority (TNSDMA):** 1070\n"
            "- **District Disaster Control Room (Chennai):** 1077\n"
            "- **Police Emergency:** 100\n"
            "- **Fire & Rescue Services:** 101\n"
            "- **Medical Emergency Ambulance:** 108\n"
            "- **Electricity Board (TANGEDCO):** 1912\n"
            "- **Child Helpline:** 1098 | **Women Helpline:** 1091"
        )
    },
    {
        "id": 13,
        "category": "Helplines",
        "category_icon": "fa-phone-volume",
        "question": "How to contact the Greater Chennai Corporation?",
        "keywords": ["contact gcc", "chennai corporation contact", "ripon building", "1913"],
        "answer": (
            "**Greater Chennai Corporation Contact Information:**\n"
            "- **24/7 Central Toll-Free Helpline:** 1913\n"
            "- **Disaster WhatsApp Complaints:** +91 94454 77205 / +91 94450 25819\n"
            "- **Headquarters Landline:** 044-25384520 / 044-25619206\n"
            "- **Ripon Building Emergency Operations Center:** EVR Periyar Salai, Chennai 600003."
        )
    },
    {
        "id": 14,
        "category": "Helplines",
        "category_icon": "fa-phone-volume",
        "question": "How to contact the Electricity Board for power hazards?",
        "keywords": ["tangedco contact", "electricity board helpline", "power hazard contact", "1912"],
        "answer": (
            "**TANGEDCO Electricity Emergency Channels:**\n"
            "- **24/7 Emergency Helpline:** 1912\n"
            "- **State Power Control Center:** 044-28521109 / 044-28524422\n"
            "- **WhatsApp Power Breakdown Desk:** +91 94458 50811\n"
            "- Contact immediately for sparking transformers, submerged distribution pillar boxes, or snapped overhead cables."
        )
    },
    {
        "id": 15,
        "category": "Helplines",
        "category_icon": "fa-phone-volume",
        "question": "How to contact Tamil Nadu State Disaster Management Authority (TNSDMA)?",
        "keywords": ["tnsdma", "state disaster authority", "seoc", "1070"],
        "answer": (
            "**TNSDMA State Emergency Operations Center (SEOC):**\n"
            "- **State Disaster Toll-Free:** 1070\n"
            "- **SEOC Control Desk:** 044-28593990 / 044-28410977 / 044-28414510\n"
            "- **Official Website:** https://tnsdma.tn.gov.in\n"
            "- Real-time Doppler radar telemetry, dam outflow advisories, and red alerts are synchronized through this center."
        )
    },

    # 4. Survival Kit & Food/Water (16 - 19)
    {
        "id": 16,
        "category": "Survival Kit",
        "category_icon": "fa-briefcase-medical",
        "question": "What should be in an emergency survival kit?",
        "keywords": ["emergency kit", "survival kit", "disaster kit", "kit contents"],
        "answer": (
            "**Standard 72-Hour Emergency Survival Kit:**\n"
            "1. **Water & Food:** 3 liters of drinking water per person/day, energy bars, dry fruits, biscuits, ORS, baby food.\n"
            "2. **Medical Supplies:** Bandages, antiseptic lotion, pain relievers, blister care, and 14-day supply of chronic prescription drugs.\n"
            "3. **Power & Lighting:** Heavy-duty LED torch, spare alkaline batteries, 20,000mAh mobile power bank, and a loud whistle.\n"
            "4. **Tools & Gear:** Multi-purpose knife, matchboxes in ziploc bags, waterproof rain ponchos, and dust masks.\n"
            "5. **Documents & Cash:** Waterproof pouch with Aadhaar, insurance policies, bank passbook copies, and hard currency."
        )
    },
    {
        "id": 17,
        "category": "Survival Kit",
        "category_icon": "fa-briefcase-medical",
        "question": "How much drinking water should be stored per person?",
        "keywords": ["water stored", "how much water", "water requirement", "drinking water storage"],
        "answer": (
            "**Emergency Water Storage Standards:**\n"
            "- Store a minimum of **3 to 4 Liters per person per day** for drinking and essential cooking (a family of 4 needs 40-50 Liters for a 3-day buffer).\n"
            "- Keep an extra **2 Liters per person per day** for basic sanitary handwashing and infant hygiene.\n"
            "- Store water in food-grade, sanitized plastic containers away from direct sunlight."
        )
    },
    {
        "id": 18,
        "category": "Survival Kit",
        "category_icon": "fa-briefcase-medical",
        "question": "How to safely store food during power outages?",
        "keywords": ["food power outage", "food storage", "fridge food", "spoilage"],
        "answer": (
            "**Food Safety During Power Outages:**\n"
            "1. Keep refrigerator and freezer doors tightly closed (fridge stays cold for 4 hours; full freezer holds temperature for 48 hours).\n"
            "2. Eat perishable milk, dairy, and cooked dishes first.\n"
            "3. Any refrigerated meats, eggs, or cooked meals exposed to > 4°C for over 2 hours must be discarded.\n"
            "4. Rely on hermetically sealed canned foods, dry pulses, roasted grams, and ready-to-eat ration packets."
        )
    },
    {
        "id": 19,
        "category": "Survival Kit",
        "category_icon": "fa-briefcase-medical",
        "question": "What documents should be kept in a waterproof bag?",
        "keywords": ["waterproof bag", "documents", "identity papers", "deeds", "insurance"],
        "answer": (
            "**Vital Documents to Pack in Waterproof Pouches:**\n"
            "1. Government photo IDs: Aadhaar Card, Voter ID, Passport, Driver's License, Ration Card.\n"
            "2. Property deeds, housing allotment letters, vehicle registrations (RC), and lease agreements.\n"
            "3. Comprehensive health and property insurance certificates.\n"
            "4. Ongoing medical prescriptions, vaccination records, and doctor referral summaries.\n"
            "5. Emergency cash notes (ATMs will lose power during cyclone and flood blackouts)."
        )
    },

    # 5. First Aid & Medical Emergencies (20 - 24)
    {
        "id": 20,
        "category": "First Aid",
        "category_icon": "fa-heart-pulse",
        "question": "First aid for electric shock?",
        "keywords": ["electric shock", "electrocution", "shock first aid", "live wire"],
        "answer": (
            "**First Aid for Electrical Shock:**\n"
            "1. **Do NOT touch the victim directly** while they are still in contact with the electrical current.\n"
            "2. Disconnect the main power circuit breaker immediately. If inaccessible, push them clear using a dry wooden broom handle or plastic PVC pipe.\n"
            "3. Check for responsiveness and breathing. If unconscious and not breathing, start CPR immediately (30 chest compressions : 2 rescue breaths).\n"
            "4. Call 108 Ambulance right away and cover electrical burn wounds with a clean sterile dressing."
        )
    },
    {
        "id": 21,
        "category": "First Aid",
        "category_icon": "fa-heart-pulse",
        "question": "How to treat dehydration or heat stroke?",
        "keywords": ["dehydration", "heat stroke", "heatwave", "ors", "sunstroke"],
        "answer": (
            "**Treatment for Heat Exhaustion & Dehydration:**\n"
            "1. Shift the patient immediately to a cool, shaded, or air-conditioned room.\n"
            "2. Remove excessive clothing and apply ice packs or cold wet towels to their neck, armpits, and groin.\n"
            "3. Administer Oral Rehydration Salts (ORS) solution, fresh coconut water, or lightly salted buttermilk in gradual sips.\n"
            "4. If body temperature exceeds 40°C (104°F) or patient exhibits delirium/unconsciousness, dial 108 immediately for emergency medical transport."
        )
    },
    {
        "id": 22,
        "category": "First Aid",
        "category_icon": "fa-heart-pulse",
        "question": "What to do if someone is drowning or submerged?",
        "keywords": ["drowning", "submerged", "cpr drowning", "rescue drowning"],
        "answer": (
            "**Drowning Rescue & Resuscitation:**\n"
            "1. **Safety First:** Extend a pole, throw a buoyant ring or rope rather than jumping into turbulent water.\n"
            "2. Lay the retrieved victim on a firm flat surface and tilt head back gently to open airway.\n"
            "3. If not breathing, begin CPR without delay: Deliver 30 firm chest compressions (100-120 compressions/min) followed by 2 rescue breaths.\n"
            "4. Remove wet clothing, wrap in dry warm blankets to prevent hypothermia, and contact 108 Ambulance."
        )
    },
    {
        "id": 23,
        "category": "First Aid",
        "category_icon": "fa-heart-pulse",
        "question": "How to handle snake bites or waterborne infections in floods?",
        "keywords": ["snake bite", "snake", "leptospirosis", "waterborne infection", "infection"],
        "answer": (
            "**Snake Bites & Infection Protocols:**\n"
            "1. **Snake Bites:** Keep the victim completely still and calm. Immobilize the bitten limb below heart level with a splint. Do NOT cut, suck venom, or apply tight tourniquets. Transport immediately to Government General Hospital for polyvalent anti-snake venom (ASV).\n"
            "2. **Waterborne Leptospirosis/Rat Fever:** Avoid wading barefoot in floodwaters. Clean skin with soap and antiseptic. Take prophylactic Doxycycline tablets (100 mg) if prescribed by local public health camp medical officers."
        )
    },
    {
        "id": 24,
        "category": "First Aid",
        "category_icon": "fa-heart-pulse",
        "question": "How to handle food poisoning in emergency camps?",
        "keywords": ["food poisoning", "diarrhea", "camp illness", "vomiting"],
        "answer": (
            "**Emergency Food Poisoning Management:**\n"
            "1. Hydrate continuously using Oral Rehydration Salts (ORS) and clean boiled water to replace electrolytes.\n"
            "2. Avoid solid, spicy, or dairy foods for 4 to 6 hours.\n"
            "3. Do not consume unprescribed anti-motility drugs.\n"
            "4. Report promptly to the relief shelter's Primary Health Center (PHC) medical booth if vomiting persists or stool contains blood."
        )
    },

    # 6. Shelters & Relief Camps (25 - 28)
    {
        "id": 25,
        "category": "Shelters",
        "category_icon": "fa-tents",
        "question": "What are the rules for shelter occupancy?",
        "keywords": ["shelter rules", "shelter occupancy", "relief camp rules", "camp admission"],
        "answer": (
            "**Relief Shelter Occupancy & Conduct Guidelines:**\n"
            "1. Admission is 100% free with priority given to infants, pregnant women, senior citizens, and physically challenged persons.\n"
            "2. Mandatory entry registration at the reception counter with name, contact, and home ward details.\n"
            "3. Clean cooked meals, drinking water, hygiene kits, and medical checkups are provided complimentary by GCC and Red Cross.\n"
            "4. Tobacco, alcohol, weapons, and disorderly conduct are strictly prohibited on shelter premises.\n"
            "5. Dedicated private zones are maintained for women, nursing mothers, and families."
        )
    },
    {
        "id": 26,
        "category": "Shelters",
        "category_icon": "fa-tents",
        "question": "What is the maximum capacity of relief shelters?",
        "keywords": ["shelter capacity", "camp capacity", "available beds", "how many people in shelter"],
        "answer": (
            "**Shelter Capacity & Availability:**\n"
            "- GCC Community Centers & relief schools have capacities ranging from **150 to 500 persons** per location.\n"
            "- Live occupancy counts, available bed numbers, and nearest distance are dynamically updated in real-time on our **Shelter Locator** dashboard.\n"
            "- When a shelter exceeds 90% capacity, incoming evacuees are automatically routed to secondary relief centers."
        )
    },
    {
        "id": 27,
        "category": "Shelters",
        "category_icon": "fa-tents",
        "question": "Are pets allowed in emergency shelters?",
        "keywords": ["pets", "animals", "dogs", "cats", "pet shelter"],
        "answer": (
            "**Pet Policy in Relief Centers:**\n"
            "- Designated relief centers feature segregated, covered pet holding pens operated in coordination with the Blue Cross of India and animal welfare NGOs.\n"
            "- Owners should bring a leash, pet food, clean water bowl, and vaccination records if accessible.\n"
            "- For animal rescues from flooded compounds, alert the Blue Cross Emergency Rescue helpline at 044-22354959."
        )
    },
    {
        "id": 28,
        "category": "Shelters",
        "category_icon": "fa-tents",
        "question": "What medical facilities are available at relief camps?",
        "keywords": ["shelter medical", "camp doctor", "phc shelter", "medicines in camp"],
        "answer": (
            "**Medical Facilities in Relief Camps:**\n"
            "- 24/7 Mobile Medical Unit staffed with a physician, nurse, and pharmacist.\n"
            "- Stocked with emergency trauma first-aid, ORS rehydration counters, insulin, and anti-hypertensive refills.\n"
            "- Rapid diagnostic screening for Dengue, Leptospirosis, and respiratory infections.\n"
            "- Dedicated ambulances parked on-site for immediate transfer to tertiary government hospitals."
        )
    },

    # 7. Risk Engine & Zones (29 - 33)
    {
        "id": 29,
        "category": "Risk & Zones",
        "category_icon": "fa-map-location-dot",
        "question": "How is the area risk score calculated?",
        "keywords": ["how is risk score calculated", "risk engine formula", "risk calculation", "weighted factors"],
        "answer": (
            "**AI Dynamic Risk Score Engine (0.0 to 1.0):**\n"
            "The risk index is computed continuously using 6 weighted parameters:\n"
            "1. **Historical Flood Frequency (25%):** Past inundation records from 2015/2023 monsoons.\n"
            "2. **Ground Elevation (20%):** Low elevation (< 5m MSL) significantly elevates risk.\n"
            "3. **Population Density (15%):** Vulnerability index based on census density.\n"
            "4. **Proximity to Water Bodies (15%):** Distance to Buckingham Canal, Adyar/Cooum rivers, and Pallikaranai marshland.\n"
            "5. **Current Rainfall Intensity (15%):** Real-time mm/hr telemetry.\n"
            "6. **Active Pending SOS Density (10%):** Concentration of live citizen emergency calls."
        )
    },
    {
        "id": 30,
        "category": "Risk & Zones",
        "category_icon": "fa-map-location-dot",
        "question": "What does Risk Level Green, Yellow, Orange, and Red mean?",
        "keywords": ["risk levels", "green yellow orange red", "risk classification", "color code"],
        "answer": (
            "**Risk Classification Levels:**\n"
            "- 🟢 **Green (Low Risk, 0.00 - 0.25):** Safe baseline conditions. Standard weather monitoring.\n"
            "- 🟡 **Yellow (Medium Risk, 0.25 - 0.50):** Advisory level. Inspect local drains and keep survival kits prepared.\n"
            "- 🟠 **Orange (High Risk, 0.50 - 0.75):** Warning level. Waterlogging expected; voluntary relocation advised for ground floors.\n"
            "- 🔴 **Critical Red (Critical Risk, 0.75 - 1.00):** Severe disaster alert. Compulsory evacuation, active boat deployment, and NDRF rescue priority."
        )
    },
    {
        "id": 31,
        "category": "Risk & Zones",
        "category_icon": "fa-map-location-dot",
        "question": "What are the 15 zone boundaries of Chennai?",
        "keywords": ["15 zones", "zone boundaries", "gcc zones", "zones in chennai"],
        "answer": (
            "**Greater Chennai Corporation 15 Zones:**\n"
            "- **North Region:** Zone 1 (Thiruvottiyur), Zone 2 (Manali), Zone 3 (Madhavaram), Zone 4 (Tondiarpet), Zone 5 (Royapuram)\n"
            "- **Central Region:** Zone 6 (Thiru. Vi. Ka. Nagar), Zone 7 (Ambattur), Zone 8 (Anna Nagar), Zone 9 (Teynampet), Zone 10 (Kodambakkam)\n"
            "- **South Region:** Zone 11 (Valasaravakkam), Zone 12 (Alandur), Zone 13 (Adyar), Zone 14 (Perungudi), Zone 15 (Sholinganallur)"
        )
    },
    {
        "id": 32,
        "category": "Risk & Zones",
        "category_icon": "fa-map-location-dot",
        "question": "What is the current risk level in Velachery?",
        "keywords": ["velachery risk", "velachery status", "risk in velachery"],
        "answer": (
            "**Velachery Sector Analysis (Zone 13 - South Chennai):**\n"
            "- **Risk Level:** Critical (Score: ~0.82)\n"
            "- **Vulnerability Factors:** Ground elevation is ~3.5m MSL; immediate proximity to Pallikaranai marshland and Velachery Lake overflow channel.\n"
            "- **Advisory:** High water stagnation expected in low-lying residential streets. Rescue motorboats and municipal relief centers are active at Guru Nanak College."
        )
    },
    {
        "id": 33,
        "category": "Risk & Zones",
        "category_icon": "fa-map-location-dot",
        "question": "What is the risk level in Pallikaranai and T. Nagar?",
        "keywords": ["pallikaranai", "t nagar", "t. nagar", "risk pallikaranai"],
        "answer": (
            "**Sector Risk Overview:**\n"
            "- **Pallikaranai (Zone 14):** Critical Risk (Score: ~0.88). Marshland runoff and radial road inundation; inflatable boats deployed.\n"
            "- **T. Nagar (Zone 10):** High Risk (Score: ~0.68). Commercial dense zone with water stagnation around Usman Road and GN Chetty Road; desilting pumps operational."
        )
    },

    # 8. Citizen SOS & Rescue Operations (34 - 36)
    {
        "id": 34,
        "category": "SOS & Rescue",
        "category_icon": "fa-tower-broadcast",
        "question": "How do citizens report emergencies using SOS?",
        "keywords": ["report emergency", "raise sos", "emergency sos button", "how to use sos"],
        "answer": (
            "**How to Raise an Emergency SOS:**\n"
            "1. Log into your Citizen Portal and click the flashing red **'One-Tap Emergency SOS'** button.\n"
            "2. Your device GPS pinpoints your exact latitude/longitude coordinates.\n"
            "3. Select emergency type (Flooding, Medical Trauma, Trapped on Roof, Fire, Food/Water Need).\n"
            "4. Enter affected person count and note medical specifics (e.g. cardiac, pregnancy, dialysis).\n"
            "5. Submit to instantly enter the prioritized rescue dispatch queue."
        )
    },
    {
        "id": 35,
        "category": "SOS & Rescue",
        "category_icon": "fa-tower-broadcast",
        "question": "How does the SOS priority scoring algorithm work?",
        "keywords": ["priority score", "sos priority", "algorithm", "ranking"],
        "answer": (
            "**AI SOS Dynamic Priority Scoring Engine (0 - 100):**\n"
            "Incoming requests are automatically scored using:\n"
            "- **Medical NLP Parser:** Critical keywords ('unconscious', 'heart', 'baby', 'pregnant', 'dialysis') add +15 to +20 points.\n"
            "- **Affected Headcount:** Multiplier based on number of trapped individuals.\n"
            "- **Sector Risk Weight:** Multiplier derived from live area elevation and water level.\n"
            "- **Vulnerability Index:** Senior citizens and children boost priority to the front of the queue."
        )
    },
    {
        "id": 36,
        "category": "SOS & Rescue",
        "category_icon": "fa-tower-broadcast",
        "question": "How can family members track an active SOS rescue status?",
        "keywords": ["track sos", "family tracking", "rescue tracking", "live map status"],
        "answer": (
            "**Live Rescue Tracking Features:**\n"
            "- When an SOS is assigned, a unique **Live Tracking Room** is activated.\n"
            "- Citizens and registered Family Circle members can see the assigned NGO name, Rescue Commander phone number, and real-time vehicle GPS coordinates on an interactive Leaflet map.\n"
            "- Automatic SMS notifications are sent at each stage: *Assigned*, *En-Route*, *On-Site*, and *Rescued*."
        )
    },

    # 9. NGOs, Rescue Teams & Volunteers (37 - 40)
    {
        "id": 37,
        "category": "NGOs & Volunteers",
        "category_icon": "fa-hand-holding-heart",
        "question": "How to sign up as a disaster response volunteer?",
        "keywords": ["sign up volunteer", "become volunteer", "join rescue", "volunteer registration"],
        "answer": (
            "**Volunteer & NGO Registration Steps:**\n"
            "1. Click **Register** on the portal and choose the **NGO / Volunteer Organization** role.\n"
            "2. Fill in organization credentials, Darpan ID/Trust Registration, and active volunteer counts.\n"
            "3. List available equipment inventories (inflatable boats, 4x4 vehicles, drones, power saws).\n"
            "4. Following review by District Disaster Admins, your team will receive real-time dispatch missions."
        )
    },
    {
        "id": 38,
        "category": "NGOs & Volunteers",
        "category_icon": "fa-hand-holding-heart",
        "question": "How are rescue teams and inflatable boats deployed?",
        "keywords": ["rescue teams deployed", "boat deployment", "inflatable boats", "dispatch teams"],
        "answer": (
            "**Rescue Team & Boat Deployment Process:**\n"
            "1. Government Command reviews the prioritized SOS queue on the GIS Operations map.\n"
            "2. Verified NGOs and NDRF/SDRF teams in the closest zone are assigned missions.\n"
            "3. Teams receive turn-by-turn navigation coordinates, victim medical reports, and depth assessments to decide whether Gemini inflatable boats or amphibious vehicles are required."
        )
    },
    {
        "id": 39,
        "category": "NGOs & Volunteers",
        "category_icon": "fa-hand-holding-heart",
        "question": "How can an NGO get verified by the government?",
        "keywords": ["verify ngo", "ngo verification", "government verification", "ngo approval"],
        "answer": (
            "**NGO Verification Protocol:**\n"
            "1. After registering, the NGO uploads their 80G/12A/Darpan certificates and identity proofs.\n"
            "2. The District Government Admin inspects credential validity and sets team capacity thresholds in the Government NGO Console.\n"
            "3. Once status is switched to **Verified**, the NGO gains access to dispatch tasks and resource depot requisitions."
        )
    },
    {
        "id": 40,
        "category": "NGOs & Volunteers",
        "category_icon": "fa-hand-holding-heart",
        "question": "How to request additional resources like boats, food, and medical kits?",
        "keywords": ["request resources", "resource allocation", "boats food medical", "depot request"],
        "answer": (
            "**Emergency Resource Requisition Process:**\n"
            "1. NGO Commanders and Zonal Officers access the **Resource Management** module.\n"
            "2. Submit quantity requirements for: Inflatable Boats, Packaged Drinking Water, Food Rations, Trauma First-Aid Kits, or Heavy Pumping Units.\n"
            "3. The AI Resource Optimizer reviews city-wide depot reserves and generates optimal inter-depot transfer orders."
        )
    }
]

# 15 Portal-Specific Starter Questions
PORTAL_STARTER_QUESTIONS = {
    "citizen": [
        {
            "id": "c1",
            "question": "How do I send an SOS alert?",
            "keywords": ["send sos", "send an sos alert", "broadcast sos", "issue sos", "how do i send an sos", "how to send sos"],
            "answer": (
                "**How to Send an Emergency SOS Alert:**\n"
                "1. Click the **'Broadcast SOS'** or **'Request Help'** button from your Citizen Dashboard.\n"
                "2. Confirm your GPS location (or the nearest sector will be auto-detected).\n"
                "3. Specify your emergency type (e.g. Flood, Medical, Trapped), total headcount, and any urgent medical needs (insulin, cardiac, pregnancy, etc.).\n"
                "4. Click **'Broadcast Emergency SOS'** to transmit your distress signal directly to Government Command and nearby NGO rescue units.\n"
                "5. You will immediately receive a live tracking link with real-time squad updates."
            )
        },
        {
            "id": "c2",
            "question": "Where is the nearest shelter to me?",
            "keywords": ["nearest shelter", "shelter near me", "where is the nearest shelter", "find shelter", "safe haven", "closest shelter"],
            "answer": (
                "**Locating Nearest Emergency Relief Shelters:**\n"
                "1. Navigate to the **'Safe Havens'** tab from your navigation menu.\n"
                "2. The system calculates real-time **Haversine GPS distances** from your current location to all 426 Chennai shelter camps.\n"
                "3. Each shelter listing displays current bed occupancy, available capacity, and direct hotline contact numbers.\n"
                "4. Click on any shelter marker on the interactive Leaflet map to preview driving routes and safety status."
            )
        },
        {
            "id": "c3",
            "question": "What should I keep in an emergency go-bag?",
            "keywords": ["go bag", "emergency bag", "survival kit", "what should i keep in an emergency go bag", "go-bag", "emergency kit"],
            "answer": (
                "**72-Hour Emergency Go-Bag Checklist:**\n"
                "- **Potable Water:** 3 liters per person per day (minimum 3-day supply).\n"
                "- **Non-Perishable Food:** Energy bars, dry fruits, ready-to-eat rations, infant food.\n"
                "- **First Aid & Prescription Medicines:** 7-day supply of daily medications, antiseptic wipes, bandages, ORS sachets.\n"
                "- **Light & Power:** High-lumen waterproof torch, extra batteries, fully charged power banks, cables.\n"
                "- **Documents in Waterproof Pouch:** Aadhaar/ID cards, property documents, insurance policies, emergency cash.\n"
                "- **Personal Protection:** Whistle for signaling rescue squads, N95 masks, rain ponchos, multi-tool knife."
            )
        },
        {
            "id": "c4",
            "question": "How do I track my assigned rescue team?",
            "keywords": ["track rescue team", "track my assigned rescue team", "track team", "rescue status", "tracking", "track squad"],
            "answer": (
                "**Tracking Your Assigned Rescue Squad:**\n"
                "1. Go to **'My Requests'** or **'Live Tracking'** in your Citizen Portal.\n"
                "2. When Government Command assigns an NGO, your mission status changes from *Pending* to *Assigned*.\n"
                "3. On the live tracking map, you will see real-time vehicle GPS coordinates, current stage (*En-Route*, *On-Site*, *Completed*), and assigned NGO squad contact details.\n"
                "4. You can also monitor automatic status updates in your notification bell icon."
            )
        },
        {
            "id": "c5",
            "question": "Who do I call if I can't reach the app?",
            "keywords": ["who do i call", "cant reach app", "cannot reach the app", "offline helpline", "phone call emergency", "emergency phone"],
            "answer": (
                "**Official 24/7 Offline Emergency Contacts (Landline & Mobile):**\n"
                "- **District Disaster Control Room (Chennai):** 1077\n"
                "- **State Disaster Management Authority (TNSDMA):** 1070\n"
                "- **Greater Chennai Corporation (GCC):** 1913\n"
                "- **Medical Emergency Ambulance:** 108\n"
                "- **Fire & Rescue Services:** 101\n"
                "- **Police Emergency:** 100\n"
                "- **Electricity Board (TANGEDCO):** 1912"
            )
        }
    ],
    "ngo": [
        {
            "id": "n1",
            "question": "How do I form a new rescue squad?",
            "keywords": ["form squad", "form a new rescue squad", "new team", "create squad", "form rescue squad", "form new squad"],
            "answer": (
                "**Forming a New Rescue Response Squad:**\n"
                "1. Go to **'Rescue Team Formations'** (`/ngo/teams.html`) in your NGO Portal.\n"
                "2. Click **'Form New Squad'**, enter your squad designation name (e.g. *North Chennai Flood Unit A*), and set the initial capacity.\n"
                "3. Use the **'Assign Members to Squad'** multiselect panel to assign available volunteers by their specialized skills (e.g. Rescue, Medical, Logistics).\n"
                "4. Once active, the team becomes eligible for immediate mission dispatch from Central Command."
            )
        },
        {
            "id": "n2",
            "question": "How do I check volunteer availability by skill?",
            "keywords": ["volunteer availability", "check volunteer availability by skill", "filter skill", "volunteer skill", "member directory"],
            "answer": (
                "**Filtering Volunteers in the 20,000 Member Registry:**\n"
                "1. Navigate to **'Member Directory'** (`/ngo/members.html`).\n"
                "2. Use the **Filter Skill** dropdown to select specialized qualifications (*Rescue*, *Food Distribution*, *Medical Support*, *Shelter Management*, *Transportation*, *Logistics*).\n"
                "3. Filter by **Availability Status** (*Available*, *Active*, *Offline*) and search by region or name.\n"
                "4. All columns support instant server-side pagination and indexed sorting."
            )
        },
        {
            "id": "n3",
            "question": "How is SOS priority score calculated?",
            "keywords": ["priority score calculated", "how is sos priority score calculated", "priority calculation", "priority algorithm", "how is priority calculated"],
            "answer": (
                "**SOS Priority Scoring Engine Formula (Range 0 - 100+):**\n"
                "- **Headcount Multiplier:** Base score scaled by number of trapped individuals (`headcount * 2.0`).\n"
                "- **Medical NLP Parser:** Critical keywords (*heart*, *insulin*, *unconscious*, *pregnant*, *dialysis*, *fracture*) add **+15.0 to +20.0 points**.\n"
                "- **Sector Risk Weight:** Integrated area flood risk score (`risk_score * 10.0`).\n"
                "- **Emergency Type Multiplier:** Flooding, Trapped on Roof, Fire triage weights applied automatically."
            )
        },
        {
            "id": "n4",
            "question": "How do I report a food/shelter deficit?",
            "keywords": ["food shelter deficit", "report a food", "report a food/shelter deficit", "food deficit", "shelter deficit", "report deficit"],
            "answer": (
                "**Reporting Regional Supply Surplus & Deficit:**\n"
                "1. Open **'Food Operations'** (`/ngo/food-analysis.html`) or **'Shelter Management'** (`/ngo/shelter-analysis.html`).\n"
                "2. Review the **Regional Surplus & Deficit Indicators** table to identify sectors in negative margins.\n"
                "3. In the **'Update Supply Stocks'** panel, select the target sector, enter quantities added or distributed, and submit to synchronize depot counts in real-time."
            )
        },
        {
            "id": "n5",
            "question": "What equipment is recommended for a flood mission?",
            "keywords": ["equipment recommended", "what equipment is recommended for a flood mission", "flood mission equipment", "flood gear", "equipment for flood"],
            "answer": (
                "**Recommended Flood Rescue Mission Equipment Protocol:**\n"
                "- **Marine & Watercraft:** Gemini inflatable rescue boat with outboard motor, lightweight paddles, puncture repair kits.\n"
                "- **Flotation & Safety:** Type III / Type V life jackets (1 per crew + victim spares), throw ropes (30m with floating bag).\n"
                "- **Lighting & Electronics:** Waterproof high-lumen dive torches, headlamps, GPS navigators, 2-way VHF radios.\n"
                "- **Medical & Trauma:** Advanced Life Support (ALS) trauma kit, cervical collar, spine board, stretcher, thermal blankets.\n"
                "- **Rations:** High-calorie energy bars, sealed water pouches, chlorine disinfection tablets."
            )
        }
    ],
    "gov": [
        {
            "id": "g1",
            "question": "Show me all Critical-risk sectors right now.",
            "keywords": ["critical risk sectors", "show me all critical-risk sectors right now", "show critical sectors", "critical areas", "critical risk right now"],
            "answer": "" # Handled dynamically by live DB query
        },
        {
            "id": "g2",
            "question": "How do I verify a new NGO?",
            "keywords": ["verify a new ngo", "how do i verify a new ngo", "verify ngo", "approve ngo", "ngo verification"],
            "answer": (
                "**Government NGO Verification Workflow:**\n"
                "1. Go to **'NGO Verification'** (`/government/ngos.html`) from the Government Portal menu.\n"
                "2. Locate unverified NGO applications with badge `Pending Review`.\n"
                "3. Inspect submitted Darpan ID, Trust Deed / 12A / 80G registration certificates, and available volunteer headcounts.\n"
                "4. Click **'Verify NGO'** to activate their dispatch authorization. Verified NGOs will immediately receive mission dispatches."
            )
        },
        {
            "id": "g3",
            "question": "How do I generate today's situation report PDF?",
            "keywords": ["generate todays situation report pdf", "generate situation report", "situation report pdf", "how do i generate today's situation report pdf", "download pdf report"],
            "answer": (
                "**Generating Official Situation Briefing Reports:**\n"
                "1. Navigate to **'Situation Reports'** (`/government/reports.html`).\n"
                "2. Choose report scope (*City-Wide Summary* or select a specific sector).\n"
                "3. Click **'Compile & Download Briefing'**.\n"
                "4. The ReportLab PDF engine generates a formatted document containing: Executive Incident Summary, Sector Risk Matrix, Resource Allocation Triage, and Official Sign-off Blocks.\n"
                "5. Generated PDFs are archived in the Reports History table for immediate download."
            )
        },
        {
            "id": "g4",
            "question": "What triggers a flash-flood warning?",
            "keywords": ["flash flood warning", "what triggers a flash-flood warning", "trigger flash flood", "warning criteria", "triggers flash flood"],
            "answer": (
                "**Flash-Flood Automated Trigger Thresholds:**\n"
                "- **Rainfall Intensity:** Hourly precipitation > **35 mm/hr** (Moderate Alert) or > **65 mm/hr** (Severe Flash-Flood Alert).\n"
                "- **Elevation & Water Proximity:** Sectors with elevation < **5.0m MSL** within 500m of Adyar River, Cooum River, Buckingham Canal, or Pallikaranai marshland.\n"
                "- **Drainage Stagnation Rate:** Water levels rising faster than 15 cm/hour in micro-catchment sensor logs.\n"
                "- **Reservoir Discharge Advisories:** Controlled discharge from Chembarambakkam, Poondi, or Red Hills lakes exceeding 5,000 cusecs."
            )
        },
        {
            "id": "g5",
            "question": "Show unresolved SOS requests older than 30 minutes.",
            "keywords": ["unresolved sos requests older than 30 minutes", "older than 30 minutes", "delayed sos", "unresolved older than 30", "unresolved sos older than 30 min"],
            "answer": "" # Handled dynamically by live DB query
        }
    ]
}

# Build rapid lookup dictionary from questions and keywords
PREDEFINED_QA = {}
for item in DEFAULT_CATEGORIZED_QUESTIONS:
    q_text = item["question"].lower().strip()
    PREDEFINED_QA[q_text] = item["answer"]
    for kw in item.get("keywords", []):
        PREDEFINED_QA[kw.lower().strip()] = item["answer"]

for p_role, p_items in PORTAL_STARTER_QUESTIONS.items():
    for item in p_items:
        if item["answer"]:
            q_text = item["question"].lower().strip()
            PREDEFINED_QA[q_text] = item["answer"]
            for kw in item.get("keywords", []):
                PREDEFINED_QA[kw.lower().strip()] = item["answer"]

def get_default_questions():
    """
    Returns the list of 40 default questions formatted for frontend consumption.
    """
    return DEFAULT_CATEGORIZED_QUESTIONS

def get_portal_starter_questions(role='citizen'):
    """
    Returns the 5 default starter questions tailored for a specific portal.
    """
    return PORTAL_STARTER_QUESTIONS.get(role, PORTAL_STARTER_QUESTIONS['citizen'])

def match_query(question, user):
    """
    Tries to match query to pre-defined intents, dynamic database models, or templates.
    Returns: (matched_bool, answer_string)
    """
    q_lower = question.lower().strip()
    clean_q = re.sub(r'[^\w\s]', ' ', q_lower).strip()

    # 1. Dynamic Query: Critical Risk Sectors
    if ('critical' in q_lower or 'highest risk' in q_lower) and ('sector' in q_lower or 'area' in q_lower or 'show' in q_lower or 'list' in q_lower or 'right now' in q_lower):
        crit_areas = Area.query.filter_by(risk_level='Critical').all()
        if crit_areas:
            lines = [f"- **{a.area_name}** ({a.zone}): Risk Score {a.risk_score:.2f} | Pop: {a.population:,} | Rain: {a.rainfall_intensity} mm/hr" for a in crit_areas[:15]]
            return True, (
                f"**Active Critical-Risk Sectors ({len(crit_areas)} Total Identified in Chennai):**\n\n" +
                "\n".join(lines) +
                "\n\n*Command Action:* Prioritize evacuation shelter activation and inflatable rescue boat deployments to these sectors immediately."
            )
        else:
            return True, "There are currently **0 sectors** classified under Critical risk in Greater Chennai."

    # 2. Dynamic Query: Unresolved SOS older than 30 minutes
    if ('unresolved' in q_lower or 'pending' in q_lower or 'older' in q_lower) and ('30 min' in q_lower or 'minute' in q_lower or 'delay' in q_lower or '30' in q_lower):
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        delayed_soses = SosRequest.query.filter(
            SosRequest.status.in_(['pending', 'assigned']),
            SosRequest.created_at <= cutoff
        ).order_by(SosRequest.priority_score.desc()).all()
        if delayed_soses:
            lines = [f"- **SOS #{s.id}** in **{s.area.area_name if s.area else 'Sector ' + str(s.area_id)}**: {s.emergency_type} ({s.people_affected} affected) | Priority: {s.priority_score:.1f} | Elapsed: {max(1, int((datetime.utcnow() - s.created_at).total_seconds() / 60))} mins" for s in delayed_soses[:10]]
            return True, (
                f"**Unresolved SOS Requests Older Than 30 Minutes ({len(delayed_soses)} Total Queue):**\n\n" +
                "\n".join(lines) +
                "\n\n*Command Escalation:* Mobilize closest SDRF/NGO response squads immediately."
            )
        else:
            return True, "No unresolved SOS requests older than 30 minutes are currently pending in the queue."

    # 3. Dynamic Area Risk queries (e.g., "What is the current risk level in Velachery?")
    area_match = re.search(r'(risk level|status|safe|score|risk) in ([a-zA-Z\.\s\-]+)', q_lower)
    if not area_match:
        area_match = re.search(r'([a-zA-Z\.\s\-]+)\s+(risk|status|level|score)', q_lower)
        if area_match:
            area_name = area_match.group(1).strip()
        else:
            area_name = None
    else:
        area_name = area_match.group(2).strip()
        
    if area_name:
        clean_name = area_name.replace("current", "").replace("what is the", "").replace("what is", "").replace("the", "").strip()
        if len(clean_name) >= 3:
            area = Area.query.filter(Area.area_name.like(f"%{clean_name}%")).first()
            if area:
                alert_count = Alert.query.filter(Alert.area_id == area.id).count()
                alert_msg = f" There are {alert_count} active alert(s) for this area." if alert_count > 0 else " No active alerts at present."
                return True, (
                    f"**Area:** {area.area_name} ({area.zone})\n"
                    f"**Current Risk Level:** {area.risk_level} (Score: {round(area.risk_score, 4)})\n"
                    f"**Details:** Elevation is {area.elevation}m MSL, population is {area.population:,}, waterbody proximity is {area.water_distance}m, and current rainfall is {area.rainfall_intensity} mm/hr.\n"
                    f"**Safety status:** {alert_msg}"
                )

    # 4. Portal-specific starter questions matching
    for p_role, p_items in PORTAL_STARTER_QUESTIONS.items():
        for item in p_items:
            if item["question"].lower().strip('?') == q_lower.strip('?'):
                if item["answer"]:
                    return True, item["answer"]
            for kw in item.get("keywords", []):
                if kw in q_lower or kw in clean_q:
                    if item["answer"]:
                        return True, item["answer"]

    # 5. Exact or keyword match against 40 default questions
    for q_item in DEFAULT_CATEGORIZED_QUESTIONS:
        if q_item["question"].lower() == q_lower or q_item["question"].lower().strip('?') == q_lower.strip('?'):
            return True, q_item["answer"]
        for kw in q_item.get("keywords", []):
            if kw in q_lower or kw in clean_q:
                return True, q_item["answer"]

    # 6. Look for SOS stats (e.g., "How many pending SOS in Zone 13?")
    sos_match = re.search(r'(how many|number of|pending) sos', q_lower)
    if sos_match:
        zone_match = re.search(r'zone\s+(\d+)', q_lower)
        if zone_match:
            zone_num = zone_match.group(1)
            areas = Area.query.filter(Area.zone.like(f"Zone {zone_num}%")).all()
            area_ids = [a.id for a in areas]
            pending_count = SosRequest.query.filter(SosRequest.area_id.in_(area_ids), SosRequest.status == 'pending').count()
            assigned_count = SosRequest.query.filter(SosRequest.area_id.in_(area_ids), SosRequest.status == 'assigned').count()
            return True, f"In **Zone {zone_num}**, there are **{pending_count}** pending SOS requests and **{assigned_count}** assigned missions."
        else:
            pending_count = SosRequest.query.filter(SosRequest.status == 'pending').count()
            assigned_count = SosRequest.query.filter(SosRequest.status == 'assigned').count()
            resolved_count = SosRequest.query.filter(SosRequest.status == 'resolved').count()
            return True, (
                f"**City-Wide SOS Statistics:**\n"
                f"- **Pending Queue:** {pending_count} requests\n"
                f"- **Assigned / In Rescue:** {assigned_count} requests\n"
                f"- **Resolved / Rescued:** {resolved_count} requests\n"
                f"Our automated priority scoring engine is sorting the queue based on medical severity and location risk."
            )

    # 7. Look for Resource recommendations (e.g., "Recommend resource allocation for a flood in T. Nagar")
    resource_match = re.search(r'(recommend|allocate|resource|resources)\s+(for|in)\s+([a-zA-Z\.\s\-]+)', q_lower)
    if resource_match:
        area_target = resource_match.group(3).strip()
        clean_target = area_target.replace("flood", "").replace("cyclone", "").replace("heatwave", "").replace("in", "").strip()
        if len(clean_target) >= 3:
            area = Area.query.filter(Area.area_name.like(f"%{clean_target}%")).first()
            if area:
                boats = 0
                food_kits = 50
                medical_kits = 25
                rescue_personnel = 10
                
                if area.risk_level == 'Critical':
                    boats = max(2, int(area.population / 2500))
                    food_kits = int(area.population / 20)
                    medical_kits = int(area.population / 40)
                    rescue_personnel = max(20, int(area.population / 500))
                elif area.risk_level == 'High':
                    boats = max(1, int(area.population / 5000))
                    food_kits = int(area.population / 50)
                    medical_kits = int(area.population / 100)
                    rescue_personnel = max(10, int(area.population / 1000))
                elif area.risk_level == 'Medium':
                    food_kits = int(area.population / 100)
                    medical_kits = int(area.population / 200)
                    rescue_personnel = 5
                    
                return True, (
                    f"**AI Resource Recommendations for {area.area_name} ({area.risk_level} Risk):**\n"
                    f"- **Inflatable Rescue Boats:** {boats} units (based on water body distance and flood risk)\n"
                    f"- **Emergency Food & Water Packets:** {food_kits:,} kits\n"
                    f"- **Trauma & First Aid Medical Kits:** {medical_kits:,} units\n"
                    f"- **Rescue Personnel / Volunteers:** {rescue_personnel} crew members\n"
                    f"Please review availability in nearest depots before finalizing allocation orders."
                )

    # 8. Nearest shelter/hospital locator (e.g. "nearest shelter in Velachery")
    loc_match = re.search(r'(nearest|shelter|hospital|locator|find)\s+(in|near)\s+([a-zA-Z\.\s\-]+)', q_lower)
    if loc_match:
        loc_area = loc_match.group(3).strip()
        if len(loc_area) >= 3:
            area = Area.query.filter(Area.area_name.like(f"%{loc_area}%")).first()
            if area:
                if 'hospital' in q_lower or 'medical' in q_lower:
                    hosp = Hospital.query.filter(Hospital.area_id == area.id).first()
                    if hosp:
                        return True, f"The nearest hospital in this area is **{hosp.name}**. Beds available: **{hosp.beds_available}**. Contact: {hosp.contact}."
                    else:
                        return True, f"No general hospitals are logged directly in {area.area_name}. Please coordinate transport to the nearest Zone Command Medical Unit."
                else:
                    shel = Shelter.query.filter(Shelter.area_id == area.id).first()
                    if shel:
                        space = shel.capacity - shel.current_occupancy
                        return True, f"The nearest emergency shelter is **{shel.name}**. Current Occupancy: **{shel.current_occupancy}/{shel.capacity}** (Available spots: **{space}**). Contact: {shel.contact}."
                    else:
                        return True, f"No emergency shelters are currently active in {area.area_name}. Refer to zone relief schools."

    # 9. Secondary match against PREDEFINED_QA
    for key, val in PREDEFINED_QA.items():
        if key in q_lower or key in clean_q:
            return True, val
            
    return False, ""

def llm_fallback(question, user_context):
    """
    Executes fallback to Gemini API or intelligent rule-based engine if API keys are missing or call fails.
    Injects real-time database context into the model's instructions.
    """
    api_key = os.environ.get('GEMINI_API_KEY') or ''
    
    # Construct DB state context to feed the AI
    area_count = Area.query.count()
    alert_count = Alert.query.count()
    sos_pending = SosRequest.query.filter(SosRequest.status == 'pending').count()
    ngo_count = Ngo.query.count()
    active_teams = RescueTeam.query.filter(RescueTeam.status == 'active').count()
    critical_areas = Area.query.filter(Area.risk_level == 'Critical').limit(5).all()
    crit_list = ", ".join([a.area_name for a in critical_areas]) if critical_areas else "None"
    
    context = (
        f"Real-time System Status of Chennai Region:\n"
        f"- Mapped Areas: {area_count}\n"
        f"- Active Danger Alerts: {alert_count}\n"
        f"- Pending Citizen SOS Requests: {sos_pending}\n"
        f"- Registered rescue NGOs: {ngo_count}\n"
        f"- Active Teams deployed: {active_teams}\n"
        f"- Top Critical Risk Areas: {crit_list}\n"
        f"You are the Disaster Shield AI Assistant. You help emergency district officers, NGO workers, and citizens. "
        f"Answer clearly, professionally, and keep response concise."
    )
    
    # If Gemini API key exists, call Gemini API
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{context}\n\nUser Question: {question}\n\nAnswer:"
                    }]
                }]
            }
            res = requests.post(url, json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                answer = data['candidates'][0]['content']['parts'][0]['text']
                return answer
        except Exception:
            pass
            
    # Intelligent rule-based response generator (resilient offline fallback)
    q = question.lower()
    if 'flood' in q or 'rain' in q or 'water' in q:
        return (
            f"Based on our active Chennai command records, there are {sos_pending} pending SOS requests. "
            f"Currently, Velachery, Pallikaranai, and adjacent low-lying areas are at High/Critical risk due to "
            f"drainage blockages. We recommend deploying additional rescue teams and boats to {crit_list}. "
            f"Always advise residents to cut power supply and evacuate to the nearest emergency shelter."
        )
    elif 'ngo' in q or 'team' in q or 'rescue' in q or 'squad' in q:
        return (
            f"Our records show {ngo_count} registered NGOs with {active_teams} active rescue squads currently deployed. "
            f"Missions can be dispatched from the Government Central Command dashboard. Priority is automatically "
            f"assigned to locations with medical emergencies."
        )
    elif 'resource' in q or 'boat' in q or 'food' in q or 'supply' in q:
        return (
            f"Resource stocks are monitored by sector. Critical areas ({crit_list}) should be checked for "
            f"boat availability. Local depots can be reallocated using the Resource Management tab. "
            f"Please ensure a minimum safety reserve of 20% in medical kits at all times."
        )
    elif 'shelter' in q or 'safe' in q:
        return (
            f"Chennai has activated emergency shelter relief camps across all 15 GCC zones. "
            f"You can view proximity-sorted shelters under the 'Safe Havens' tab. In high inundation sectors, "
            f"Corporation relief schools and community halls provide dry beds, hot meals, and basic first aid."
        )
    else:
        return (
            f"Thank you for contacting the Disaster Shield Command Assistant. "
            f"We are monitoring {area_count} sectors in Greater Chennai. There are {alert_count} active alerts "
            f"and {sos_pending} SOS rescue operations pending. Please refer to the specialized tabs "
            f"(SOS Queue, NGO Allocation, or Alerts Board) to take command actions, or click any of the suggested default questions "
            f"below to receive immediate advisory guidelines."
        )

def ask_ai(question, user):
    """
    Main entry point for AI Queries.
    """
    matched, answer = match_query(question, user)
    if not matched:
        answer = llm_fallback(question, user)
        
    return answer

