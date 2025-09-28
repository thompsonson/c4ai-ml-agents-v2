# Benchmark Management Guide

This guide covers how to import, manage, and use benchmarks in the ML Agents v2 reasoning research platform.

## Overview

ML Agents v2 supports importing benchmark datasets from CSV files into a structured database for evaluation against different reasoning approaches. The system includes 62 preprocessed benchmark files covering various domains including logic, mathematics, science, programming, and more.

## Quick Start

### Import Your First Benchmark

```bash
# Import a small benchmark for testing
ml-agents benchmark import data/benchmarks/BENCHMARK-24-AIME.csv --name "AIME"

# Verify the import
ml-agents benchmark list
ml-agents benchmark show AIME
```

### Basic Commands

```bash
# List all imported benchmarks
ml-agents benchmark list

# Import a benchmark with custom name and description
ml-agents benchmark import data/benchmarks/BENCHMARK-01-GPQA.csv \
  --name "GPQA" \
  --description "Graduate-level physics, chemistry, and biology questions"

# View detailed benchmark information
ml-agents benchmark show GPQA

# Import with filename as default name
ml-agents benchmark import data/benchmarks/BENCHMARK-05-FOLIO.csv
```

## Available Benchmarks

The system includes 62 preprocessed benchmark CSV files located in `data/benchmarks/`. Here are key categories:

### Mathematics & Logic
- **AIME** (`BENCHMARK-24-AIME.csv`) - 980 questions - Competition mathematics
- **MATH3** (`BENCHMARK-22-MATH3.csv`) - 6,596 questions - Mathematical reasoning
- **FOLIO** (`BENCHMARK-05-FOLIO.csv`) - 5,127 questions - First-order logic reasoning
- **StrategyQA** (`BENCHMARK-16-StrategyQA.csv`) - 8,932 questions - Multi-step reasoning

### Science & Academia
- **GPQA** (`BENCHMARK-01-GPQA.csv`) - 448 questions - Graduate-level science
- **JEE Chemistry** (`BENCHMARK-28-JEE_Chemistry.csv`) - 10,757 questions
- **JEE Physics** (`BENCHMARK-31-JEE_Physics.csv`) - 15,059 questions
- **SciBench** (`BENCHMARK-33-SciBench.csv`) - 2,378 questions

### Programming
- **LeetCode Python Easy** (`BENCHMARK-42-LeetCode_Python_Easy.csv`) - 21,104 questions
- **LeetCode Python Medium** (`BENCHMARK-43-LeetCode_Python_Medium.csv`) - 33,239 questions
- **MBPP** (`BENCHMARK-41-MBPP.csv`) - 4,333 questions - Python programming

### Medical & Healthcare
- **USMLE MedQA** (`BENCHMARK-49-USMLE_MedQA.csv`) - 12,600 questions
- **MedMCQA** (`BENCHMARK-50-MedMCQA.csv`) - 11,034 questions
- **PubMedQA** (`BENCHMARK-51-PubMedQA.csv`) - 5,557 questions

### Legal & Finance
- **CaseHOLD** (`BENCHMARK-26-CaseHOLD.csv`) - 15,001 questions - Legal reasoning
- **CUAD** (`BENCHMARK-27-CUAD.csv`) - 22,847 questions - Contract understanding
- **FinBen** (`BENCHMARK-59-FinBen.csv`) - 2,481 questions - Financial analysis

## CSV Format Requirements

Benchmark CSV files must include these columns:
- **INPUT**: The question text
- **OUTPUT**: The expected answer

Example CSV structure:
```csv
INPUT,OUTPUT
"What is 2 + 2?","4"
"What is the capital of France?","Paris"
```

Additional columns are preserved as metadata.

## Import Options

### Basic Import
```bash
ml-agents benchmark import data/benchmarks/BENCHMARK-01-GPQA.csv
```
- Uses filename as benchmark name
- Auto-generates description

### Custom Import
```bash
ml-agents benchmark import data/benchmarks/BENCHMARK-01-GPQA.csv \
  --name "GPQA_Custom" \
  --description "Custom description for GPQA benchmark"
```

### Import Validation
The system automatically validates:
- CSV file existence and readability
- Required INPUT/OUTPUT columns
- Question data completeness
- Benchmark name uniqueness

## Recommended Import Strategy

### 1. Start Small for Testing
```bash
# Small benchmarks for initial testing
ml-agents benchmark import data/benchmarks/BENCHMARK-24-AIME.csv --name "AIME"
ml-agents benchmark import data/benchmarks/BENCHMARK-60-IFEval.csv --name "IFEval"
```

### 2. Import Key Research Benchmarks
```bash
# Core reasoning benchmarks
ml-agents benchmark import data/benchmarks/BENCHMARK-01-GPQA.csv --name "GPQA"
ml-agents benchmark import data/benchmarks/BENCHMARK-05-FOLIO.csv --name "FOLIO"
ml-agents benchmark import data/benchmarks/BENCHMARK-22-MATH3.csv --name "MATH3"
```

### 3. Import Domain-Specific Benchmarks
```bash
# Programming benchmarks
ml-agents benchmark import data/benchmarks/BENCHMARK-41-MBPP.csv --name "MBPP"
ml-agents benchmark import data/benchmarks/BENCHMARK-42-LeetCode_Python_Easy.csv --name "LeetCode_Python_Easy"

# Science benchmarks
ml-agents benchmark import data/benchmarks/BENCHMARK-28-JEE_Chemistry.csv --name "JEE_Chemistry"
```

## Using Benchmarks for Evaluation

Once imported, benchmarks can be used with reasoning agents:

```bash
# Create evaluation (after evaluation bugs are fixed)
ml-agents evaluate create --agent none --model anthropic/claude-3-sonnet --benchmark GPQA

# Run the evaluation
ml-agents evaluate run <evaluation-id>
```

## Database Management

### Check Imported Benchmarks
```bash
sqlite3 data/ml_agents_v2.db "SELECT name, question_count, created_at FROM preprocessed_benchmarks;"
```

### Remove Benchmark
```bash
sqlite3 data/ml_agents_v2.db "DELETE FROM preprocessed_benchmarks WHERE name='BENCHMARK_NAME';"
```

### Database Location
- **Development**: `data/ml_agents_v2.db`
- **Schema**: Defined in `src/ml_agents_v2/infrastructure/database/models/benchmark.py`

## Troubleshooting

### Common Issues

**"Benchmark name already exists"**
```bash
# Check existing benchmarks
ml-agents benchmark list

# Use different name or remove existing benchmark
ml-agents benchmark import file.csv --name "NewName"
```

**"CSV file not found"**
```bash
# Verify file path
ls data/benchmarks/BENCHMARK-*.csv

# Use absolute path if needed
ml-agents benchmark import /full/path/to/benchmark.csv
```

**"Invalid CSV format"**
- Ensure CSV has INPUT and OUTPUT columns
- Check for proper UTF-8 encoding
- Verify CSV is not corrupted

### Import Validation Errors
The system provides detailed error messages for:
- Missing required columns
- Empty questions or answers
- File access issues
- Format problems

### Recovery Options
```bash
# Re-import after fixing issues
ml-agents benchmark import data/benchmarks/BENCHMARK-01-GPQA.csv --name "GPQA_Fixed"

# Check import status
ml-agents benchmark show GPQA_Fixed
```

## Architecture Notes

The benchmark import system follows Domain-Driven Design principles:

- **Infrastructure Layer**: `BenchmarkCsvReader` handles file I/O and format conversion
- **Application Layer**: `BenchmarkProcessor` orchestrates import workflow
- **Domain Layer**: `PreprocessedBenchmark` and `Question` entities remain pure
- **CLI Layer**: Commands provide user interface with rich formatting

Questions are converted from CSV format to domain objects:
- Sequential IDs generated ("1", "2", "3"...)
- INPUT → question text
- OUTPUT → expected answer
- Additional columns → metadata

## Best Practices

1. **Start Small**: Import smaller benchmarks first for testing
2. **Consistent Naming**: Use clear, descriptive benchmark names
3. **Verify Import**: Always check with `benchmark show` after import
4. **Document Purpose**: Use descriptive descriptions for research context
5. **Backup Database**: Regular backups before major imports

## Next Steps

1. Import benchmarks for your research domain
2. Wait for evaluation creation bug fixes
3. Test None reasoning agent with imported benchmarks
4. Scale to additional reasoning approaches (Chain of Thought, etc.)

For more information, see the complete documentation in `/documentation/` directory.