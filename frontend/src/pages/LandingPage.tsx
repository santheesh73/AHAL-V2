import { CTASection } from "../components/landing/CTASection"
import { ComparisonSection } from "../components/landing/ComparisonSection"
import { FeatureGrid } from "../components/landing/FeatureGrid"
import { HeroSection } from "../components/landing/HeroSection"
import { ProductShowcase } from "../components/landing/ProductShowcase"
import { WorkflowSection } from "../components/landing/WorkflowSection"

export function LandingPage() {
  return (
    <div className="relative">
      <HeroSection />
      <FeatureGrid />
      <WorkflowSection />
      <ProductShowcase />
      <ComparisonSection />
      <CTASection />
    </div>
  )
}
