# Hybrid Iterative Approach for VistA-M Repository Analysis

## Overview

The hybrid iterative approach balances comprehensive discovery with practical delivery timelines. It uses representative sampling and iterative refinement to discover patterns efficiently while maintaining confidence in schema design decisions.

## Philosophy

- **Discovery-Driven**: Learn from the code, don't impose assumptions
- **Sample-Based**: Use representative samples rather than exhaustive processing
- **Iterative**: Refine understanding through multiple cycles
- **Pragmatic**: Balance thoroughness with delivery constraints
- **Stakeholder-Engaged**: Include stakeholder feedback in schema development

## Timeline: 4-5 Weeks

### Week 1: Repository Reconnaissance & Sampling
### Week 2-3: Discovery Parser Development & Pattern Analysis
### Week 4: Schema Generation & Validation
### Week 5: Production Parser & Final Implementation

---

## Phase 1: Repository Reconnaissance & Sampling (Week 1)

### Objective
Understand repository structure and create representative samples for efficient pattern discovery.

### Day 1-2: Repository Analysis

```bash
# Initial repository assessment
cd VistA-M/
find . -type f -name "*.m" | wc -l     # Count MUMPS routines
find . -type f -name "*.zwr" | wc -l   # Count global files
ls -la Packages/                        # Package organization
head -20 Packages.csv                   # Package metadata
```

### Day 3-4: Strategic Sampling

```python
class StrategicSampler:
    """Create representative samples for efficient analysis"""
    
    def create_stratified_sample(self, repo_path, sample_size=200):
        """Create samples across different dimensions"""
        
        samples = {
            'size_stratified': self.sample_by_file_size(),
            'package_stratified': self.sample_by_package(),
            'complexity_stratified': self.sample_by_complexity(),
            'random_sample': self.random_sample(50)
        }
        
        return self.deduplicate_samples(samples)
    
    def sample_by_file_size(self):
        """Sample files across size distribution"""
        # Small files (< 100 lines): 20%
        # Medium files (100-500 lines): 50%  
        # Large files (500+ lines): 30%
        
    def sample_by_package(self):
        """Ensure all packages represented"""
        # At least 5 files from each package
        # More from larger packages
        
    def sample_by_complexity(self):
        """Sample across complexity spectrum"""
        # Simple routines (few labels, basic patterns)
        # Complex routines (many labels, intricate patterns)
```

### Day 5: Sample Validation & Pattern Documentation

Create initial pattern catalog from samples to guide discovery parser development.

```markdown
# Initial Pattern Catalog (Sample-Based)

## High-Confidence Patterns
- Routine headers: `ROUTINE ;;version;package`  
- Labels: Non-indented lines with identifiers
- Calls: `D LABEL^ROUTINE`, `$$FUNC^ROUTINE`
- Globals: `^GLOBAL(subscripts)`

## Medium-Confidence Patterns  
- Version information in line 2
- Comment patterns with `;`
- FileMan field references
- Cross-package dependencies

## Questions for Discovery Parser
- Are there dynamic call patterns?
- What global naming conventions exist?
- How consistent are routine structures?
- What anomalies appear in samples?
```

---

## Phase 2: Discovery Parser Development & Pattern Analysis (Week 2-3)

### Objective
Build iterative discovery parser that focuses on samples first, then scales to full repository.

### Week 2: Discovery Parser v1

```python
class HybridDiscoveryParser:
    """Sample-based discovery with iterative refinement"""
    
    def __init__(self, samples):
        self.samples = samples
        self.patterns_found = {
            'confirmed_patterns': {},
            'potential_patterns': {},
            'anomalies': {},
            'questions_raised': []
        }
    
    def parse_samples_iteratively(self):
        """Parse samples in batches, refining understanding"""
        
        # Start with smallest, simplest files
        simple_batch = self.samples['size_stratified']['small']
        simple_patterns = self.parse_batch(simple_batch)
        
        # Refine parser based on simple patterns
        self.refine_parser_logic(simple_patterns)
        
        # Parse medium complexity files
        medium_batch = self.samples['size_stratified']['medium']
        medium_patterns = self.parse_batch(medium_batch)
        
        # Identify new patterns and update parser
        new_patterns = self.identify_new_patterns(simple_patterns, medium_patterns)
        self.update_parser_logic(new_patterns)
        
        # Parse complex files
        complex_batch = self.samples['size_stratified']['large']
        complex_patterns = self.parse_batch(complex_batch)
        
        return self.consolidate_patterns([simple_patterns, medium_patterns, complex_patterns])
    
    def parse_routine_file(self, file_path):
        """Parse single routine with current understanding"""
        
        routine_data = {
            'file_info': self.extract_file_metadata(file_path),
            'structure': self.analyze_routine_structure(file_path),
            'labels': self.extract_labels(file_path),
            'calls': self.extract_calls(file_path),
            'globals': self.extract_global_references(file_path),
            'anomalies': self.identify_anomalies(file_path)
        }
        
        return routine_data
    
    def extract_calls(self, file_path):
        """Extract call patterns with increasing sophistication"""
        
        calls = []
        
        with open(file_path) as f:
            for line_num, line in enumerate(f):
                # Standard DO calls
                do_calls = self.extract_do_calls(line)
                calls.extend(do_calls)
                
                # Function calls ($$)
                func_calls = self.extract_function_calls(line)
                calls.extend(func_calls)
                
                # Check for unusual patterns
                unusual = self.check_unusual_call_patterns(line)
                if unusual:
                    self.patterns_found['questions_raised'].append({
                        'file': file_path,
                        'line': line_num,
                        'pattern': unusual,
                        'question': 'Is this a valid call pattern?'
                    })
        
        return calls
```

### Week 3: Pattern Analysis & Refinement

```python
class PatternAnalyzer:
    """Analyze discovered patterns and generate insights"""
    
    def analyze_sample_patterns(self, sample_results):
        """Comprehensive analysis of sample parsing results"""
        
        analysis = {
            'pattern_frequency': self.calculate_pattern_frequencies(sample_results),
            'pattern_consistency': self.assess_pattern_consistency(sample_results),
            'anomaly_analysis': self.analyze_anomalies(sample_results),
            'relationship_patterns': self.discover_relationships(sample_results),
            'entity_candidates': self.identify_entity_candidates(sample_results)
        }
        
        return analysis
    
    def generate_schema_hypotheses(self, pattern_analysis):
        """Generate schema candidates based on discovered patterns"""
        
        # Schema 1: Code-Focused
        code_schema = {
            'name': 'Detailed Code Analysis',
            'motivation': 'High frequency of label-to-label calls suggests procedure-focused analysis',
            'entities': ['Routine', 'Label', 'Statement', 'Variable'],
            'relationships': ['CONTAINS', 'CALLS', 'REFERENCES', 'DEFINES'],
            'evidence': pattern_analysis['pattern_frequency']['calls'],
            'use_cases': ['Refactoring', 'Impact analysis', 'Code quality']
        }
        
        # Schema 2: Architecture-Focused  
        arch_schema = {
            'name': 'System Architecture',
            'motivation': 'Cross-package references suggest architectural analysis needed',
            'entities': ['Package', 'Module', 'Interface', 'DataStore'],
            'relationships': ['DEPENDS_ON', 'EXPOSES', 'IMPLEMENTS', 'ACCESSES'],
            'evidence': pattern_analysis['relationship_patterns']['cross_package'],
            'use_cases': ['Modernization', 'API design', 'System understanding']
        }
        
        # Schema 3: Data-Focused
        data_schema = {
            'name': 'Data Flow Analysis', 
            'motivation': 'Global variable patterns suggest data-centric view needed',
            'entities': ['DataEntity', 'Processor', 'Accessor', 'Transformer'],
            'relationships': ['READS', 'WRITES', 'TRANSFORMS', 'VALIDATES'],
            'evidence': pattern_analysis['pattern_frequency']['globals'],
            'use_cases': ['Security audit', 'Compliance', 'Data governance']
        }
        
        return [code_schema, arch_schema, data_schema]
```

---

## Phase 3: Schema Generation & Validation (Week 4)

### Objective
Generate multiple schema options from discovered patterns and validate them against broader samples.

### Schema Validation Process

```python
class SchemaValidator:
    """Validate schema hypotheses against broader data"""
    
    def validate_schema_hypothesis(self, schema, validation_samples):
        """Test schema against additional data"""
        
        validation_results = {
            'coverage_test': self.test_coverage(schema, validation_samples),
            'accuracy_test': self.test_accuracy(schema, validation_samples),
            'completeness_test': self.test_completeness(schema, validation_samples),
            'scalability_test': self.test_scalability(schema, validation_samples)
        }
        
        return self.score_schema(validation_results)
    
    def test_coverage(self, schema, samples):
        """What percentage of discovered patterns does schema capture?"""
        
        captured_patterns = 0
        total_patterns = 0
        
        for sample_file in samples:
            file_patterns = self.extract_patterns_from_file(sample_file)
            total_patterns += len(file_patterns)
            
            for pattern in file_patterns:
                if self.schema_captures_pattern(schema, pattern):
                    captured_patterns += 1
        
        return captured_patterns / total_patterns if total_patterns > 0 else 0
    
    def recommend_schema_refinements(self, validation_results):
        """Suggest improvements based on validation"""
        
        refinements = []
        
        if validation_results['coverage_test'] < 0.8:
            missing_patterns = self.identify_missing_patterns(validation_results)
            refinements.append({
                'type': 'add_entities',
                'suggestion': f'Add entities for: {missing_patterns}',
                'evidence': 'Coverage test shows missing patterns'
            })
        
        if validation_results['accuracy_test'] < 0.9:
            refinements.append({
                'type': 'refine_relationships',
                'suggestion': 'Relationship definitions need clarification',
                'evidence': 'Accuracy test shows mismatched extractions'
            })
        
        return refinements
```

### Schema Selection Framework

```python
def select_optimal_schema(validated_schemas, stakeholder_input):
    """Choose best schema based on validation and stakeholder needs"""
    
    selection_criteria = {
        'technical_score': 0.4,    # Validation test results
        'stakeholder_fit': 0.3,    # How well it meets stated needs  
        'implementability': 0.2,   # How practical to build
        'maintainability': 0.1     # Long-term sustainability
    }
    
    scored_schemas = []
    for schema in validated_schemas:
        score = calculate_weighted_score(schema, selection_criteria, stakeholder_input)
        scored_schemas.append((schema, score))
    
    return sorted(scored_schemas, key=lambda x: x[1], reverse=True)[0][0]
```

---

## Phase 4: Production Parser & Implementation (Week 5)

### Objective
Build production-quality parser based on selected schema and validate on full repository.

### Production Parser Architecture

```python
class VistAProductionParser:
    """Production parser optimized for selected schema"""
    
    def __init__(self, schema, discovery_insights):
        self.schema = schema
        self.insights = discovery_insights
        self.performance_optimizations = self._build_optimizations()
    
    def parse_full_repository(self, repo_path):
        """Parse entire repository efficiently"""
        
        # Progressive parsing with validation
        results = {
            'nodes': [],
            'relationships': [],
            'metadata': {
                'schema_used': self.schema['name'],
                'parsing_confidence': {},
                'anomalies_found': []
            }
        }
        
        # Process files in optimized order
        file_queue = self.optimize_processing_order(repo_path)
        
        for file_path in file_queue:
            try:
                file_results = self.parse_file_optimized(file_path)
                results['nodes'].extend(file_results['nodes'])
                results['relationships'].extend(file_results['relationships'])
                
                # Track parsing confidence
                confidence = self.assess_parsing_confidence(file_results)
                results['metadata']['parsing_confidence'][file_path] = confidence
                
            except Exception as e:
                results['metadata']['anomalies_found'].append({
                    'file': file_path,
                    'error': str(e),
                    'action': 'manual_review_required'
                })
        
        return results
    
    def parse_file_optimized(self, file_path):
        """Parse single file with schema-specific optimizations"""
        
        # Use insights from discovery phase for efficient extraction
        if file_path.endswith('.m'):
            return self.parse_routine_file(file_path)
        elif file_path.endswith('.zwr'):
            return self.parse_global_file(file_path)
        else:
            return self.parse_other_file(file_path)
```

---

## Iterative Refinement Process

### Continuous Validation Loop

```python
class IterativeRefinementEngine:
    """Continuously improve parser based on results"""
    
    def refine_parser_iteratively(self, parser, sample_results):
        """Improve parser based on sample results"""
        
        refinements_needed = self.identify_refinement_needs(sample_results)
        
        for refinement in refinements_needed:
            if refinement['type'] == 'pattern_extraction':
                self.improve_pattern_extraction(parser, refinement)
            elif refinement['type'] == 'relationship_detection':
                self.improve_relationship_detection(parser, refinement)
            elif refinement['type'] == 'anomaly_handling':
                self.improve_anomaly_handling(parser, refinement)
        
        return self.validate_refinements(parser, sample_results)
    
    def identify_refinement_needs(self, results):
        """What needs improvement in current parser?"""
        
        needs = []
        
        # Check extraction accuracy
        if results['extraction_accuracy'] < 0.95:
            needs.append({
                'type': 'pattern_extraction',
                'priority': 'high',
                'evidence': 'Missing or incorrect pattern extractions'
            })
        
        # Check relationship accuracy  
        if results['relationship_accuracy'] < 0.90:
            needs.append({
                'type': 'relationship_detection',
                'priority': 'medium', 
                'evidence': 'Incorrect or missing relationships'
            })
        
        return needs
```

---

## Advantages of Hybrid Iterative Approach

### Balanced Efficiency
- **Faster delivery**: 4-5 weeks vs 6 weeks for pure discovery
- **Resource efficient**: Focused processing on representative samples
- **Iterative learning**: Improve understanding progressively

### Risk Management
- **Early validation**: Test assumptions on samples before full commitment
- **Stakeholder engagement**: Get feedback during development process
- **Adaptive approach**: Adjust direction based on discoveries

### Practical Focus
- **Solution-oriented**: Focus on patterns that matter for analysis goals
- **Implementation-ready**: Produces production parser as final output
- **Maintainable**: Simpler than pure discovery, more robust than schema-first

---

## Disadvantages of Hybrid Iterative Approach

### Potential Blind Spots
- **Sampling bias**: May miss patterns not present in samples
- **Rare pattern loss**: Low-frequency but important patterns might be missed
- **Scale surprises**: Patterns that only emerge at full scale

### Complexity Management
- **Multiple iterations**: More complex project management
- **Validation overhead**: Need to validate multiple schema hypotheses
- **Stakeholder coordination**: Requires ongoing stakeholder engagement

---

## Success Metrics

### Discovery Quality
- **Pattern accuracy**: >95% of extracted patterns are valid
- **Coverage completeness**: >90% of actual patterns discovered
- **Anomaly identification**: <5% of files produce unexpected results

### Schema Quality  
- **Validation scores**: Selected schema scores >85% on all validation tests
- **Stakeholder satisfaction**: Schema meets stated analysis requirements
- **Implementation feasibility**: Production parser successfully processes full repository

### Project Success
- **Timeline adherence**: Project delivers on time within 4-5 week window
- **Resource efficiency**: Stays within allocated resource constraints
- **Output quality**: Final parser produces high-quality graph database

---

## Risk Mitigation Strategies

### Sampling Risks
- **Diverse sampling**: Use multiple sampling strategies (size, package, complexity)
- **Sample validation**: Validate samples against known VistA patterns
- **Iterative expansion**: Gradually expand sample size if needed

### Schema Risks
- **Multiple hypotheses**: Generate 3-5 schema options to reduce single-point failure
- **Stakeholder validation**: Get stakeholder input on schema selection
- **Fallback options**: Maintain backup schemas if primary choice fails

### Implementation Risks
- **Incremental deployment**: Test production parser on subsets before full deployment  
- **Performance monitoring**: Monitor parsing performance and accuracy continuously
- **Manual review process**: Plan for manual review of anomalies and edge cases

---

## Deliverables

### Week 1 Deliverables
- Repository structure analysis report
- Representative sample sets (200-300 files)
- Initial pattern catalog
- Sampling strategy documentation

### Week 2-3 Deliverables  
- Discovery parser (versions 1-3)
- Sample parsing results
- Pattern analysis report
- Schema hypotheses (3-5 options)

### Week 4 Deliverables
- Schema validation results
- Selected schema with justification
- Refined schema documentation
- Implementation plan

### Week 5 Deliverables
- Production parser implementation
- Full repository parsing results
- Graph database export files
- Final analysis report
- User documentation

---

## When to Use Hybrid Iterative Approach

### Ideal For
- **Balanced requirements**: Need both thoroughness and delivery speed
- **Active stakeholders**: Stakeholders available for iterative feedback
- **Moderate complexity**: System complex enough to need discovery but not overwhelming
- **Practical goals**: Analysis goals are specific and well-defined

### Not Ideal For
- **Maximum thoroughness required**: Pure discovery approach better
- **Immediate results needed**: Schema-first approach faster
- **Minimal stakeholder involvement**: Limited feedback opportunities
- **Highly experimental analysis**: Unknown analysis goals make iteration difficult

---

## Conclusion

The hybrid iterative approach provides an optimal balance between comprehensive discovery and practical delivery constraints. By using representative sampling and iterative refinement, it captures the most important patterns while delivering results in a reasonable timeframe. This approach works best when stakeholders can provide ongoing feedback and analysis goals are reasonably well-defined, making it ideal for most VistA modernization and analysis projects.