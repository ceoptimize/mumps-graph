Please explore the VistA repository folder below. Look at all the packages, globals (.zwr), and routines (.m), paying special attention to the ^DD global file. Take your time to understand how this whole codebase works together.

Vista-M-source-code

Document your findings in a markdown file - whatever seems interesting or important about how the system is structured, including basic patterns, caveats, where things are, edge cases, and anything else you would do as a skilled analyst researching this codebase. 

After exploring, explain how you would build a graph database representation of this codebase. Based on your exploration, identify:
- Which files/data sources would provide what information for the graph
- Why you chose those specific sources
- How they connect to create a complete picture

This graph should support use cases like:
- Learning file/field structures
- Code generation
- Impact analysis
- Dependency tracking
- Data flow visualization
- Migration planning

Keep the graph design practical - complex enough to be accurate and useful, but not overengineered. Focus on representing what actually exists in the code, not an idealized version.

