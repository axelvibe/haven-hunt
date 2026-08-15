# HavenHunt Design Specification

This document outlines the design specification for HavenHunt, an AI-driven property search assistant leveraging the Property Price Register (PPR) and demo rental listings in Ireland.

## Solution Concept

HavenHunt aims to revolutionize property search in Ireland by providing users with an intuitive, conversational interface that interprets raw sales data from the PPR alongside simulated rental listings. Our solution caters to first-time buyers, investors, and renters, helping them navigate the complexities of the market with clarity and confidence. 

### How It Works
Users interact with our Telegram chatbot to inquire about property sales and rentals in specific counties or eircodes. The chatbot fetches real-time data from the PPR, summarizes it, and presents insights, while also providing demo rental listings. The assistant guides users through their queries, offering personalized recommendations and clarifying any ambiguities regarding property features or pricing.

## Persona & Journey

### Target User
**First-Time Homebuyer**: A young professional in Dublin, overwhelmed by high prices and complex market dynamics, seeking guidance on property purchases.

### Key Jobs-To-Be-Done
- Understand historical sale prices in an area.
- Compare sale prices across different counties.
- Shortlist demo rentals that fit their budget and preferences.

### Core User Flows
1. **Querying Sale Prices**: 
   - User asks about recent sales in a specific county (e.g., "What homes sold in Dublin last month?").
   - The bot responds with a summary of sales, including prices and addresses, noting missing data clearly.

2. **Comparing Prices**:
   - User requests to compare sale prices across counties (e.g., "How do prices in Cork compare to Galway?").
   - The bot provides a comparative summary of average sales in both counties.

3. **Shortlisting Rentals**:
   - User asks for demo rentals within a specific price range (e.g., "Show me demo rentals under €1,500 in Galway.").
   - The bot presents a list of demo rentals, ensuring users are aware that these are simulated listings.

## Conversation Design

### Intent Recognition
- **Counties**: Recognize mentions of counties (e.g., Dublin, Cork).
- **Eircodes**: Identify eircodes from user queries.
- **EUR Price Ranges**: Understand price ranges (e.g., "under €300,000").

### Clarifying Questions
- If a user query lacks specificity, the bot prompts for clarification (e.g., "Which county are you interested in?").

### Presentation of PPR Sales
- Sales data must be presented with clear indications of missing fields, e.g., "Sale price: €350,000 (no beds recorded)."
- Users are informed about `**` prices indicating non-full market prices.

### Recommendations & Follow-Ups
- After presenting data, the bot can suggest similar areas or properties based on user preferences, maintaining a conversational tone.

## Product Architecture

### Components
- **Chatbot**: Handles user interactions and queries.
- **Search Layer**: Processes user requests and fetches data from the PPR.
- **PPR Providers**: Interfaces with the Property Price Register API.
- **Geocoder**: Converts eircodes to geographical coordinates using Google Maps or OpenStreetMap.
- **Web Presence**: Hosts the landing page and an embedded chat widget.

### Module Structure
- `product/bot/`: Contains the chatbot's logic and handlers.
- `product/listings/`: Manages property data and interactions with the PPR.
- `product/web/`: Hosts the web interface and API.
- `product/shared/`: Contains shared utilities and configurations.

## Feature Scope

### MVP Must-Haves
- A functioning Telegram chatbot with basic queries about sales and demo rentals.
- Integration with the PPR to fetch and display sale prices.
- Clear handling of missing data and `**` price indicators.
- Basic user flows for querying sales, comparing prices, and listing demo rentals.

### Should-Haves
- Enhanced filtering options by price range and features.
- User authentication for personalized experiences.
- A feedback mechanism for users to report issues or requests.

### Later Features
- Advanced analytics for market trends.
- Integration of user preferences to refine property recommendations.
- Mobile app version of the chatbot.

### Acceptance Criteria for MVP
- The chatbot must accurately fetch and display sales data from the PPR.
- Missing fields must be clearly indicated in responses.
- The sales-only rule must be enforced, with no rental listings sourced from the PPR.

## Brand & Voice

### Personality
**Irish, Friendly, Trustworthy**

### Tagline Candidates
- "Your guide to Irish property."
- "Navigate the Irish market with ease."
- "Uncover the story behind every sale."

## Risks & Design Decisions

### Potential Failures
- **PPR Data Quirks**: Opaque sale prices and missing features could confuse users.
- **No Official API**: Reliance on community APIs may lead to stability issues.
- **Geocoding without a Key**: Limited fallback options if Google Maps API is unavailable.

### Design Choices to Mitigate Risks
- Clearly communicate limitations of the PPR data to users.
- Implement robust error handling for API calls.
- Provide fallback options for geocoding to ensure functionality without reliance on a single service.

---

## Handoff to Maker
I am passing on a complete design specification for HavenHunt, detailing the solution concept, user personas and journeys, conversation design, product architecture, feature scope, brand voice, and risk management. I recommend the next agent focus on developing the product based on this specification, ensuring a user-centric approach throughout the build process.