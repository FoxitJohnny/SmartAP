"""
Example Plugin: Custom Risk Agent

This agent demonstrates how to create a custom risk assessment agent
with company-specific risk rules.
"""

import time
from typing import Dict, Any, List

from src.plugins import BaseRiskAgent, AgentContext, AgentResult, AgentStatus


class CustomRiskAgent(BaseRiskAgent):
    """
    Custom risk assessment agent with company-specific rules.
    
    This example shows how to:
    1. Implement custom risk assessment logic
    2. Check against company blacklists
    3. Apply business-specific thresholds
    4. Return structured risk assessments
    
    Usage:
        >>> from plugins.custom_risk import CustomRiskAgent
        >>> from src.plugins import AgentContext, register_agent
        >>> 
        >>> # Register the agent
        >>> agent = CustomRiskAgent()
        >>> register_agent(agent)
        >>> 
        >>> # Use in pipeline
        >>> context = AgentContext(
        ...     invoice_id="123",
        ...     pdf_bytes=pdf_data,
        ...     extracted_data={"vendor": {"name": "Acme Corp"}, "total_amount": 50000}
        ... )
        >>> result = await agent.process(context)
        >>> print(result.data["risk_level"])  # HIGH, MEDIUM, or LOW
    """
    
    def __init__(self):
        super().__init__(
            name="custom_risk_agent",
            version="1.0.0",
            description="Company-specific risk assessment with custom rules",
            risk_threshold=0.5  # Risk score threshold
        )
        
        # Company-specific configuration
        self.vendor_blacklist = [
            "Suspicious Vendor Inc",
            "Fraudulent Corp",
            "Banned Supplier Ltd"
        ]
        
        self.high_risk_countries = ["XX", "YY", "ZZ"]  # ISO country codes
        
        self.amount_thresholds = {
            "high": 100000,  # Over $100k requires extra review
            "medium": 10000,  # Over $10k requires approval
            "auto_approve": 1000  # Under $1k can be auto-approved
        }
        
        self.new_vendor_threshold_days = 90  # Vendors < 90 days are "new"
    
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method - assess invoice risk.
        """
        start_time = time.time()
        
        try:
            # Check if we have extracted data
            if not context.extracted_data:
                return AgentResult(
                    success=False,
                    status=AgentStatus.FAILED,
                    data={},
                    confidence=0.0,
                    errors=["No extracted data available for risk assessment"]
                )
            
            # Perform risk assessment
            risk_assessment = await self.assess_risk(context.extracted_data)
            
            # Add context metadata
            risk_assessment["context"] = {
                "invoice_id": context.invoice_id,
                "vendor_id": context.vendor_id,
                "assessment_timestamp": time.time()
            }
            
            # Determine confidence based on data completeness
            confidence = self._calculate_confidence(context.extracted_data)
            
            result = AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data=risk_assessment,
                confidence=confidence,
                execution_time_ms=(time.time() - start_time) * 1000,
                agent_version=self.version
            )
            
            # Add warnings if any
            if risk_assessment["risk_score"] > 0.7:
                result.warnings.append(f"High risk score: {risk_assessment['risk_score']:.2f}")
            
            return result
        
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)],
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def assess_risk(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment.
        """
        risk_factors = []
        risk_score = 0.0
        
        # 1. Check vendor blacklist
        vendor_name = invoice_data.get("vendor", {}).get("name", "")
        if vendor_name in self.vendor_blacklist:
            risk_factors.append({
                "type": "BLACKLISTED_VENDOR",
                "severity": "CRITICAL",
                "description": f"Vendor '{vendor_name}' is on company blacklist",
                "score_impact": 0.9
            })
            risk_score += 0.9
        
        # 2. Check amount thresholds
        total_amount = invoice_data.get("total_amount", 0)
        if total_amount > self.amount_thresholds["high"]:
            risk_factors.append({
                "type": "HIGH_AMOUNT",
                "severity": "HIGH",
                "description": f"Invoice amount ${total_amount:,.2f} exceeds high threshold",
                "score_impact": 0.3
            })
            risk_score += 0.3
        elif total_amount > self.amount_thresholds["medium"]:
            risk_factors.append({
                "type": "MEDIUM_AMOUNT",
                "severity": "MEDIUM",
                "description": f"Invoice amount ${total_amount:,.2f} requires approval",
                "score_impact": 0.1
            })
            risk_score += 0.1
        
        # 3. Check for missing PO
        if not invoice_data.get("po_number"):
            risk_factors.append({
                "type": "MISSING_PO",
                "severity": "MEDIUM",
                "description": "No purchase order number provided",
                "score_impact": 0.2
            })
            risk_score += 0.2
        
        # 4. Check for unusual payment terms
        payment_terms = invoice_data.get("payment_terms", "")
        if "immediate" in payment_terms.lower() or "wire" in payment_terms.lower():
            risk_factors.append({
                "type": "UNUSUAL_TERMS",
                "severity": "MEDIUM",
                "description": f"Unusual payment terms: {payment_terms}",
                "score_impact": 0.15
            })
            risk_score += 0.15
        
        # 5. Check vendor address country (if available)
        vendor_address = invoice_data.get("vendor", {}).get("address", "")
        for country_code in self.high_risk_countries:
            if country_code in vendor_address:
                risk_factors.append({
                    "type": "HIGH_RISK_COUNTRY",
                    "severity": "HIGH",
                    "description": f"Vendor located in high-risk country: {country_code}",
                    "score_impact": 0.4
                })
                risk_score += 0.4
                break
        
        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "HIGH"
            recommended_action = "MANUAL_REVIEW"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"
            recommended_action = "APPROVAL_REQUIRED"
        else:
            risk_level = "LOW"
            recommended_action = "AUTO_APPROVE" if total_amount < self.amount_thresholds["auto_approve"] else "APPROVAL_REQUIRED"
        
        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommended_action": recommended_action,
            "requires_manual_review": risk_score >= 0.7
        }
    
    def _calculate_confidence(self, invoice_data: Dict[str, Any]) -> float:
        """Calculate confidence based on data availability"""
        required_fields = ["vendor", "total_amount"]
        available = sum(1 for field in required_fields if invoice_data.get(field))
        return available / len(required_fields)


class VendorBlacklistChecker(BaseRiskAgent):
    """
    Simple risk agent that checks vendors against a blacklist.
    
    This is a minimal example showing the simplest possible risk agent.
    """
    
    def __init__(self, blacklist: List[str] = None):
        super().__init__(
            name="vendor_blacklist_checker",
            version="1.0.0",
            description="Check vendor against company blacklist"
        )
        self.blacklist = blacklist or []
    
    async def process(self, context: AgentContext) -> AgentResult:
        """Check if vendor is blacklisted"""
        try:
            risk_assessment = await self.assess_risk(context.extracted_data or {})
            
            return AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data=risk_assessment,
                confidence=1.0  # Binary check, always confident
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)]
            )
    
    async def assess_risk(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check vendor against blacklist"""
        vendor_name = invoice_data.get("vendor", {}).get("name", "")
        
        is_blacklisted = vendor_name in self.blacklist
        
        return {
            "is_blacklisted": is_blacklisted,
            "vendor_name": vendor_name,
            "risk_level": "CRITICAL" if is_blacklisted else "LOW",
            "message": f"Vendor '{vendor_name}' is blacklisted" if is_blacklisted else "Vendor is not blacklisted"
        }
