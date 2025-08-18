#!/usr/bin/env python3
"""Test script for enhanced Reader agent structural content extraction."""

import sys
import os
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agent.reader import (
    _extract_structural_content,
    _extract_headings,
    _extract_sections,
    _identify_key_sections,
    _extract_lists,
    _extract_tables,
    _extract_citations,
    _generate_content_outline,
    _classify_content,
    _extract_enhanced_metadata
)


# Sample content for testing different content types
ACADEMIC_CONTENT = """
# Deep Learning in Medical Imaging: A Comprehensive Review

## Abstract
This paper presents a comprehensive review of deep learning applications in medical imaging. We analyze recent advances in convolutional neural networks (CNNs) and their impact on diagnostic accuracy.

## 1. Introduction
Medical imaging has undergone significant transformation with the advent of artificial intelligence. Deep learning, particularly convolutional neural networks, has shown remarkable performance in various medical imaging tasks.

### 1.1 Background
The application of machine learning in healthcare dates back to the 1970s. However, recent advances in computational power and data availability have accelerated adoption.

## 2. Methodology
Our review methodology included:
- Systematic literature search
- Inclusion criteria definition
- Quality assessment
- Data extraction

## 3. Results
### 3.1 Diagnostic Accuracy
Studies showed improvement in diagnostic accuracy:
1. Radiology: 15-20% improvement
2. Pathology: 10-15% improvement  
3. Ophthalmology: 25% improvement

### 3.2 Performance Metrics
| Model Type | Accuracy | Sensitivity | Specificity |
|------------|----------|-------------|-------------|
| CNN        | 92.5%    | 89.3%       | 94.1%       |
| ResNet     | 94.2%    | 91.7%       | 95.8%       |
| VGG        | 88.9%    | 85.2%       | 91.4%       |

## 4. Discussion
The results demonstrate significant potential for deep learning in medical imaging. However, several challenges remain:
- Data privacy concerns
- Regulatory approval requirements
- Integration with existing workflows

## 5. Conclusion
Deep learning represents a paradigm shift in medical imaging analysis. Future research should focus on addressing current limitations and expanding applications.

## References
1. Smith, J. et al. (2023). "CNN Applications in Radiology." Journal of Medical AI, 15(3), 234-251. doi:10.1000/182
2. Johnson, A. (2022). "Deep Learning for Pathology." Nature Medicine, 28, 1123-1134. arXiv:2201.12345
3. Available at: https://doi.org/10.1038/s41591-022-01234-5
"""

NEWS_CONTENT = """
Breaking: Tech Giant Announces Revolutionary AI Breakthrough

SAN FRANCISCO, March 15, 2024 - In a groundbreaking announcement today, TechCorp revealed their latest artificial intelligence system that promises to transform how we interact with technology.

According to sources close to the company, the new system represents a 10x improvement over existing solutions. "This is a game-changer," said CEO Jane Smith during a press conference this morning.

Key features include:
• Advanced natural language processing
• Real-time learning capabilities  
• Enhanced security protocols
• Cross-platform compatibility

The announcement has sent shockwaves through the tech industry, with competitors scrambling to respond. Market analysts predict this could reshape the entire AI landscape.

"We're seeing unprecedented demand from enterprise customers," reported lead engineer Mark Johnson. The system is expected to be available for beta testing next quarter.

Industry experts remain divided on the implications. Some see it as revolutionary progress, while others express concerns about potential job displacement.

The full impact of this development will likely unfold over the coming months as more details emerge.
"""

BLOG_CONTENT = """
# My Journey Learning Python: From Zero to Hero

Posted by: Alex Developer on January 10, 2024

## Introduction
Hey everyone! I wanted to share my experience learning Python over the past year. It's been quite a journey, and I hope my story can help others who are just starting out.

## Getting Started
When I first decided to learn programming, I was completely overwhelmed. There are so many languages to choose from! After researching for weeks, I settled on Python because:
1. It's beginner-friendly
2. Has a huge community
3. Versatile for many applications
4. Great job prospects

## My Learning Path
### Month 1-2: Basics
- Variables and data types
- Control structures (if/else, loops)
- Functions and modules
- Basic debugging

I spent about 2 hours daily on coding exercises. The key was consistency rather than intensity.

### Month 3-4: Intermediate Concepts
- Object-oriented programming
- File handling
- Error handling
- Working with APIs

This is where things got really interesting! I built my first real project - a weather app that pulls data from an API.

### Month 5-6: Advanced Topics
- Database integration
- Web scraping
- Data analysis with pandas
- Building web applications

## Tools That Helped
Here are the resources I found most valuable:
• Python.org official tutorial
• Codecademy interactive courses
• Real Python blog articles  
• Stack Overflow community
• Local Python meetup groups

## Projects I Built
Throughout my learning journey, I focused on practical projects:
1. Personal budget tracker
2. Web scraper for job listings
3. Data visualization dashboard
4. Simple e-commerce site

## Challenges I Faced
Learning wasn't always smooth sailing. Some major obstacles:
- Understanding object-oriented concepts
- Debugging complex errors
- Choosing the right libraries
- Staying motivated during difficult topics

## Tips for Beginners
If you're just starting your Python journey, here's my advice:
- Start with small projects
- Don't skip the fundamentals
- Join the community
- Practice every day
- Don't be afraid to ask questions

## Conclusion
One year later, I can confidently say that learning Python was one of the best decisions I've made. I've landed a junior developer role and continue learning new things every day.

Remember, everyone learns at their own pace. Be patient with yourself and enjoy the journey!

---
*What's your Python learning story? Share it in the comments below!*
"""


def test_heading_extraction():
    """Test heading extraction from different content types."""
    print("📝 Testing heading extraction...")
    
    try:
        # Test academic content
        academic_headings = _extract_headings(ACADEMIC_CONTENT)
        print(f"  ✅ Academic content: {len(academic_headings)} headings extracted")
        
        # Check for specific headings
        heading_titles = [h["title"] for h in academic_headings]
        expected_headings = ["Abstract", "Introduction", "Methodology", "Results", "Conclusion"]
        found_expected = sum(1 for expected in expected_headings 
                           if any(expected.lower() in title.lower() for title in heading_titles))
        
        print(f"    Found {found_expected}/{len(expected_headings)} expected academic headings")
        
        # Test blog content
        blog_headings = _extract_headings(BLOG_CONTENT)
        print(f"  ✅ Blog content: {len(blog_headings)} headings extracted")
        
        # Test different heading types
        heading_types = set(h["type"] for h in academic_headings + blog_headings)
        print(f"    Heading types detected: {', '.join(heading_types)}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Heading extraction test failed: {e}")
        return False


def test_section_extraction():
    """Test section extraction and content parsing."""
    print("📄 Testing section extraction...")
    
    try:
        # Extract headings first
        headings = _extract_headings(ACADEMIC_CONTENT)
        
        # Extract sections
        sections = _extract_sections(ACADEMIC_CONTENT, headings)
        print(f"  ✅ Extracted {len(sections)} sections from academic content")
        
        # Check section content
        sections_with_content = [s for s in sections if len(s.get("content", "")) > 50]
        print(f"    Sections with substantial content: {len(sections_with_content)}")
        
        # Test word count calculation
        total_words = sum(s.get("word_count", 0) for s in sections)
        print(f"    Total words in sections: {total_words}")
        
        # Test blog content sections
        blog_headings = _extract_headings(BLOG_CONTENT)
        blog_sections = _extract_sections(BLOG_CONTENT, blog_headings)
        print(f"  ✅ Blog content: {len(blog_sections)} sections extracted")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Section extraction test failed: {e}")
        return False


def test_key_section_identification():
    """Test identification of key sections like abstract, introduction, etc."""
    print("🔍 Testing key section identification...")
    
    try:
        # Test academic content
        academic_key_sections = _identify_key_sections(
            ACADEMIC_CONTENT, 
            "https://example.edu/paper.pdf", 
            "application/pdf"
        )
        
        found_sections = [section for section, data in academic_key_sections.items() 
                         if data.get("found", False)]
        print(f"  ✅ Academic content: {len(found_sections)} key sections identified")
        print(f"    Found sections: {', '.join(found_sections)}")
        
        # Test news content
        news_key_sections = _identify_key_sections(
            NEWS_CONTENT, 
            "https://news.example.com/tech-breakthrough", 
            "text/html"
        )
        
        news_found = [section for section, data in news_key_sections.items() 
                     if data.get("found", False)]
        print(f"  ✅ News content: {len(news_found)} key sections identified")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Key section identification test failed: {e}")
        return False


def test_list_extraction():
    """Test extraction of bulleted and numbered lists."""
    print("📋 Testing list extraction...")
    
    try:
        # Test academic content lists
        academic_lists = _extract_lists(ACADEMIC_CONTENT)
        print(f"  ✅ Academic content: {len(academic_lists)} lists extracted")
        
        for i, lst in enumerate(academic_lists):
            list_type = lst.get("type", "unknown")
            item_count = len(lst.get("items", []))
            print(f"    List {i+1}: {list_type} type, {item_count} items")
        
        # Test blog content lists
        blog_lists = _extract_lists(BLOG_CONTENT)
        print(f"  ✅ Blog content: {len(blog_lists)} lists extracted")
        
        # Test news content lists
        news_lists = _extract_lists(NEWS_CONTENT)
        print(f"  ✅ News content: {len(news_lists)} lists extracted")
        
        return True
    
    except Exception as e:
        print(f"  ❌ List extraction test failed: {e}")
        return False


def test_table_extraction():
    """Test extraction of table-like content."""
    print("📊 Testing table extraction...")
    
    try:
        # Test academic content (has a markdown table)
        academic_tables = _extract_tables(ACADEMIC_CONTENT)
        print(f"  ✅ Academic content: {len(academic_tables)} tables extracted")
        
        for i, table in enumerate(academic_tables):
            table_type = table.get("type", "unknown")
            row_count = table.get("row_count", 0)
            col_count = table.get("column_count", 0)
            print(f"    Table {i+1}: {table_type}, {row_count} rows, {col_count} columns")
        
        # Test with tab-separated content
        tab_content = "Name\tAge\tCity\nJohn\t25\tNew York\nJane\t30\tLos Angeles"
        tab_tables = _extract_tables(tab_content)
        print(f"  ✅ Tab-separated content: {len(tab_tables)} tables extracted")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Table extraction test failed: {e}")
        return False


def test_citation_extraction():
    """Test extraction of citations and references."""
    print("📚 Testing citation extraction...")
    
    try:
        # Test academic content (has DOI and arXiv citations)
        academic_citations = _extract_citations(ACADEMIC_CONTENT)
        print(f"  ✅ Academic content: {len(academic_citations)} citations extracted")
        
        citation_types = set(c.get("type", "unknown") for c in academic_citations)
        print(f"    Citation types found: {', '.join(citation_types)}")
        
        # Count each type
        for cit_type in citation_types:
            count = sum(1 for c in academic_citations if c.get("type") == cit_type)
            print(f"    {cit_type}: {count} citations")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Citation extraction test failed: {e}")
        return False


def test_content_classification():
    """Test content type classification."""
    print("🏷️ Testing content classification...")
    
    try:
        # Test academic content classification
        academic_classification = _classify_content(
            ACADEMIC_CONTENT, 
            "https://example.edu/paper", 
            "Deep Learning in Medical Imaging"
        )
        
        print(f"  ✅ Academic content classified as: {academic_classification['primary_type']}")
        print(f"    Confidence: {academic_classification['confidence']:.2f}")
        
        # Test news content classification
        news_classification = _classify_content(
            NEWS_CONTENT, 
            "https://news.example.com/tech", 
            "Tech Giant Announces AI Breakthrough"
        )
        
        print(f"  ✅ News content classified as: {news_classification['primary_type']}")
        print(f"    Confidence: {news_classification['confidence']:.2f}")
        
        # Test blog content classification
        blog_classification = _classify_content(
            BLOG_CONTENT, 
            "https://devblog.example.com/python-journey", 
            "My Journey Learning Python"
        )
        
        print(f"  ✅ Blog content classified as: {blog_classification['primary_type']}")
        print(f"    Confidence: {blog_classification['confidence']:.2f}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Content classification test failed: {e}")
        return False


def test_enhanced_metadata():
    """Test enhanced metadata extraction."""
    print("📊 Testing enhanced metadata extraction...")
    
    try:
        # Test academic content metadata
        academic_metadata = _extract_enhanced_metadata(
            ACADEMIC_CONTENT, 
            "https://example.edu/paper", 
            "Deep Learning in Medical Imaging"
        )
        
        print(f"  ✅ Academic metadata extracted")
        print(f"    Dates found: {len(academic_metadata.get('dates_found', []))}")
        print(f"    Authors found: {len(academic_metadata.get('authors_found', []))}")
        print(f"    Keywords: {len(academic_metadata.get('potential_keywords', []))}")
        print(f"    Reading time: {academic_metadata.get('estimated_reading_time', 'N/A')}")
        
        # Test blog content metadata
        blog_metadata = _extract_enhanced_metadata(
            BLOG_CONTENT, 
            "https://blog.example.com/python", 
            "Python Learning Journey"
        )
        
        print(f"  ✅ Blog metadata extracted")
        print(f"    Reading time: {blog_metadata.get('estimated_reading_time', 'N/A')}")
        print(f"    Numerical data points: {blog_metadata.get('numerical_data_count', 0)}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Enhanced metadata extraction test failed: {e}")
        return False


def test_complete_structural_extraction():
    """Test complete structural content extraction pipeline."""
    print("🔧 Testing complete structural extraction...")
    
    try:
        # Test full structural extraction
        structural_data = _extract_structural_content(
            ACADEMIC_CONTENT, 
            "https://example.edu/paper.pdf", 
            "application/pdf"
        )
        
        print(f"  ✅ Complete structural extraction successful")
        
        # Check all components
        components = [
            "headings", "sections", "key_sections", "lists", 
            "tables", "citations", "outline"
        ]
        
        for component in components:
            if component in structural_data:
                count = len(structural_data[component]) if isinstance(structural_data[component], list) else len(structural_data[component].keys())
                print(f"    {component}: {count} items")
            else:
                print(f"    {component}: missing")
        
        # Test with blog content
        blog_structural = _extract_structural_content(
            BLOG_CONTENT, 
            "https://blog.example.com", 
            "text/html"
        )
        
        print(f"  ✅ Blog structural extraction successful")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Complete structural extraction test failed: {e}")
        return False


async def main():
    """Run all Reader structural extraction tests."""
    print("🧪 Testing enhanced Reader agent structural content extraction...\n")
    
    tests = [
        test_heading_extraction,
        test_section_extraction,
        test_key_section_identification,
        test_list_extraction,
        test_table_extraction,
        test_citation_extraction,
        test_content_classification,
        test_enhanced_metadata,
        test_complete_structural_extraction
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test execution failed: {e}")
            results.append(False)
        print()  # Add spacing between tests
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"🏁 Reader Structural Tests: {success_count}/{total_count} passed")
    
    if success_count == total_count:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        exit(1)