# SSP_Fall2026_Research_Project

## Team

Shane Banachowski | shb0064@auburn.edu | Tasks 2 & 4
Joseph Wilkerson  | Jaw0216@auburn.edu | Task 1
Rett Wilson       | Jew0063@auburn.edu | Task 3

**Task-1 

LLM used: TBD




**Task-2 output: two Test files***
- 'element_names_diff.txt' : one KDE name per line, or 'No differences in regards to element requirement'
- 'element_requirements_diff.txt' : one 'Name,req' per line or ' No difference in regards to elemnet requirements'


**Task 3 (cisdiff/executor.py)
- 'load_text_pair' : reads the two Task-2 TEXT files
- 'map_differences_to_rules' : writes the Hadolint rules mapped to the differences, or 'NO DIFFERENCES FOUND' / 'NO MAPPING FOUND'
- 'run_hadolint' : runs Hadolint on a folder of Dockerfiles and returns a pandas DataFrame (all rules if nothing mapped, otherwise only the listed rules)
- 'write_results_csv' : writes a CSV with FilePath, DefaultSeverity, RULEID, COUNT





**Task4
1) Requirements.txt file
2) README
3) Github Actions
4) Binary
