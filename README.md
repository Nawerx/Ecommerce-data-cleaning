# E-Commerce Data Cleaning with Python and pandas

## Project Overview

This is a portfolio project focused specifically on **data cleaning and data quality work with Python and pandas**.

The dataset is small, but deliberately messy. My goal was not to build a large business analysis on top of only 100 cleaned records. Instead, I used the dataset to practice the part of analytics that comes before analysis: understanding what is wrong with raw data, deciding what can be corrected safely, validating assumptions, and leaving information missing when it cannot be recovered reliably.



The raw dataset contained **103 rows and 11 columns**. After removing exact duplicate records, the final dataset contains **100 rows**.

---

## Project Goal

The main goal of this project is to demonstrate that I can take a messy dataset and work through data-quality problems step by step instead of immediately applying automatic fixes.

I wanted the final code to reflect the way I actually solved the dataset while learning pandas. Because of that, the script is intentionally written as a clear sequential pipeline rather than being heavily abstracted into functions or classes.

The most important part of the project is not that every line is maximally optimized. It is that I understand why each transformation exists and can explain the decisions behind it.

---

## Dataset

The dataset used in this project was downloaded from Kaggle:

**Messy E-Commerce Sales Data**  
https://www.kaggle.com/datasets/kandeeldev/messy-e-commerce-sales-data

The raw file is stored at:

```text
data/raw/messy_ecommerce_sales_data.csv
```

The cleaned file is written to:

```text
data/cleaned/ecommerce_sales_cleaned.csv
```

The dataset contains the following columns:

| Column | Description |
| --- | --- |
| `ID` | Record identifier |
| `Customer_Name` | Customer name |
| `Order_ID` | Order identifier |
| `Order_Date` | Order date |
| `Product` | Product name |
| `Category` | Product category |
| `Quantity` | Number of units |
| `Price` | Unit price |
| `Payment_Method` | Payment method |
| `Status` | Order status |
| `Total` | Order total |

---

# How I Worked Through the Dataset

This section describes the cleaning process in the order in which I actually discovered the problems and made decisions.

## 1. I kept the raw data untouched

The first thing I did was load the CSV into `df_raw` and create a working copy:

```python
df_raw = pd.read_csv(RAW_PATH)
df = df_raw.copy()
```

I did this because I expected that some cleaning decisions might need to be checked against the original values later.

That became useful several times, especially when I investigated negative numeric values and wanted to compare cleaned values with the original records.

I treated the raw dataset as the source of truth and made all transformations only on the working DataFrame.

---

## 2. I first noticed problems in the column names and strings

During the initial inspection, I saw that some column names contained extra whitespace.

For example, columns such as `Customer_Name` and `Category` originally had leading spaces in their names.

I cleaned the column names with:

```python
df.rename(columns=str.strip, inplace=True)
```

Then I applied the same idea to string values inside the DataFrame.

Instead of manually selecting every string column, I checked the dtype of each column and stripped whitespace only from string columns.

This solved one general formatting problem before I started working with individual columns.

---

## 3. I normalized categorical values

The next issue was inconsistency in text categories.

Columns such as:

- `Product`
- `Category`
- `Payment_Method`
- `Status`

contained values with inconsistent capitalization.

For example, `Category` included different forms such as:

```text
Electronics
electronics
ELECTRONICS
electronic
```

I first converted the categorical text to lowercase.

After that, I noticed that lowercase normalization alone was not enough because `electronic` and `electronics` still represented the same category with different wording.

I therefore corrected the known inconsistent value:

```python
"electronic" -> "electronics"
```

Once the values were normalized, I converted the repeated low-cardinality columns to pandas `category` dtype.

At this point I was thinking mainly about consistency and correct data types. I had not yet discovered the larger Product → Category inconsistency that appeared later during restoration.

---

## 4. `Quantity` looked numeric, but pandas read it as text

When I inspected `Quantity`, I expected it to be numeric, but pandas had loaded it as a string column.

Looking at the values explained why.

Most values looked normal:

```text
1
2
3
4
5
```

but the column also contained:

```text
-2
-5
4a
```

I first explored ways to identify valid digits, but values such as missing data and `4a` made simple string checks inconvenient.

I then used:

```python
pd.to_numeric(..., errors="coerce")
```

This became an important cleaning pattern for me.

Valid numeric strings were converted to numbers, while values that could not be parsed were converted to missing values.

That allowed me to distinguish between:

- values that were originally missing,
- values that were present but invalid.

For example, `4a` was not treated as a real number and I did not try to guess what number it was supposed to be.

---

## 5. `Price` had several different kinds of dirty values

`Price` had a similar problem, but the errors were more varied.

Examples included:

```text
300$
four hundred
abd
-100
```

I did not want to treat all invalid strings the same way.

I separated values that could be interpreted reliably from values that could not.

For example:

```text
300$         -> 300
four hundred -> 400
abd          -> missing
```

`300$` could be cleaned safely by removing the currency symbol.

`four hundred` had an unambiguous numeric meaning, so I converted it to `400`.

`abd`, however, did not contain enough information to infer a price. I intentionally allowed it to become missing rather than inventing a value.

This was one of the points where I decided that **a missing value is better than an incorrect value created by the cleaning process**.

---

## 6. I originally considered removing negative values

After converting `Quantity` and `Price` to numbers, I noticed negative values.

My first reaction was that negative quantities or prices probably should not exist in this dataset.

However, instead of immediately deleting those rows, I went back to the original data and investigated the relationship between:

- `Quantity`
- `Price`
- `Total`
- `Status`

This changed my decision.

For example, some records had combinations where the negative values still followed the arithmetic relationship:

```text
Total = Price × Quantity
```

Examples in the raw data included cases such as:

```text
Quantity = -2
Price    = 10000
Total    = -20000
```

and:

```text
Quantity = 3
Price    = -100
Total    = -300
```

The records were not consistently marked as returns or cancellations. They appeared in statuses such as ordinary processing, shipped, or delivered orders.

That made the negative sign look more like a data-entry problem than meaningful business information.

Because of that investigation, I changed my original idea and corrected the sign with `.abs()` instead of deleting the rows.

This was an important lesson from the project: **a suspicious value should be investigated in context before deciding how to clean it**.

---

## 7. I discovered that `Total` could be used as a validation rule

Once `Price` and `Quantity` were cleaned, I noticed that `Total` should follow:

```text
Total = Price × Quantity
```

I did not immediately overwrite `Total`.

First, I temporarily kept the original values and compared them with a recalculated version.

That let me see whether the relationship actually held across the dataset.

The comparison showed that some original totals were incorrect, some were missing, and some negative totals were simply the result of the same sign problem found in `Price` or `Quantity`.

After validating the relationship, I recalculated:

```python
df["Total"] = df["Price"] * df["Quantity"]
```

This accomplished two things at once:

1. incorrect totals were corrected;
2. missing totals were restored when both `Price` and `Quantity` were known.

If either factor was missing, the recalculated `Total` remained missing.

I intentionally did not fill those values with an average or another estimate.

---

## 8. I checked duplicates instead of deleting repeated IDs automatically

The dataset also contained repeated identifiers.

I checked duplicated `ID` values and duplicated `Order_ID` values, but I did not assume that a repeated identifier automatically meant the row should be deleted.

I compared the complete records.

The repeated rows turned out to be exact duplicates.

The duplicated records were:

```text
ID 142
ID 146
ID 175
```

Each duplicated pair contained the same order data.

Only after confirming that the entire rows were duplicates did I remove them with:

```python
df.drop_duplicates(inplace=True)
```

This reduced the dataset from:

```text
103 rows -> 100 rows
```

The decision was based on the complete records, not only on repeated IDs.

---

## 9. `Order_Date` contained mixed formats and one invalid value

`Order_Date` was originally a string column.

When I inspected the values, I found multiple date formats, including examples such as:

```text
Jan 5 2023
5/1/2023
11/22/2024
```

and one clearly invalid value:

```text
abc
```

Because the formats were mixed, I used:

```python
pd.to_datetime(
    ...,
    format="mixed",
    errors="coerce",
    dayfirst=False
)
```

I chose `dayfirst=False` after looking at dates such as `11/22/2024`, which cannot be interpreted as day/month/year.

The value `abc` could not be recovered reliably, so it became `NaT`.

I did not replace it with an invented date.

---

## 10. I separately checked the unusual 2023 dates

After parsing the dates, I looked at the year distribution and noticed that most records were from 2025 while a few were from 2023.

At first, this looked suspicious.

Instead of deleting them as outliers, I inspected those rows individually.

The 2023 records looked like otherwise normal orders with valid products, categories, quantities, prices, totals, payment methods, and statuses.

I had no evidence that the dates were incorrect.

Therefore, I kept them.

This was another case where I chose not to treat an unusual value as an error without evidence.

---

# Data Restoration Stage

At this point I considered the main cleaning stage finished and moved to restoration.

The question became:

> Which missing values can I recover from patterns already present in the dataset?

This is where I discovered one of the most interesting problems in the project.

---

## 11. Trying to restore missing `Category` values revealed incorrect existing categories

`Category` still contained missing values.

My first goal was simply to restore those missing categories from `Product`.

I grouped the data by `Product` and inspected which categories appeared for each product.

That revealed a new problem: **the issue was not only missing categories**.

The same product sometimes appeared under different categories.

Examples included products such as:

```text
basketball
blender
lamp
microwave
t-shirt
vacuum
yoga mat
```

appearing in more than one category.

So filling only the missing values would not have been enough.

I needed to decide which category was the most likely category for each product.

---

## 12. I counted Product + Category combinations

To understand the inconsistency, I counted how often every Product + Category combination occurred.

For example, patterns looked like:

```text
basketball -> sports       5
basketball -> electronics  1

blender    -> home         7
blender    -> electronics  1

lamp       -> home         6
lamp       -> electronics  1
```

The counts made the problem much clearer.

For most products with conflicting categories, one category appeared repeatedly while another appeared only once.

That suggested that the rare category was likely the incorrect record.

---

## 13. I used the dominant category for each product

I then found the row with the highest category count for every product using `idxmax()`.

This produced a Product → Category lookup table.

For example:

```text
basketball -> sports
blender    -> home
lamp       -> home
laptop     -> electronics
shoes      -> clothing
```

I converted that lookup into a mapping and rebuilt the `Category` column from `Product`.

This did more than fill missing values.

It also corrected category values that were already present but inconsistent with the dominant mapping.

This was not something I planned from the beginning. I discovered it while trying to solve the missing-value problem.

That is why I consider the cleaning process iterative rather than a fixed sequence of transformations known in advance.

---

## 14. I reviewed the remaining missing `Price`, `Quantity`, and `Total`

After restoring `Category`, I inspected all rows where at least one of:

- `Price`
- `Quantity`
- `Total`

was still missing.

At this stage I already knew the relationship:

```text
Total = Price × Quantity
```

so I checked whether that relationship was enough to recover more values.

The remaining rows looked like cases such as:

```text
Quantity known
Price missing
Total missing
```

or:

```text
Price known
Quantity missing
Total missing
```

and one row where all three values were missing.

In those cases, there is not enough information to solve for the missing values uniquely.

For example:

```text
Quantity = 2
Price = ?
Total = ?
```

has infinitely many possible answers.

Because of that, I stopped restoration there.

I intentionally did **not** use:

- averages,
- medians,
- random values,
- guessed prices,
- guessed quantities.

For this project, preserving uncertainty was more important than producing a dataset with zero missing values.

---

## 15. I changed `Quantity` from `float64` to nullable `Int64`

After numeric cleaning, `Quantity` was stored as `float64`.

That happened because regular integer columns cannot store `NaN`.

However, quantity represents whole units, not decimal values.

I therefore changed it to pandas nullable integer type:

```python
df["Quantity"] = df["Quantity"].astype("Int64")
```

This allows values such as:

```text
1
2
3
<NA>
```

instead of:

```text
1.0
2.0
3.0
NaN
```

I made this change for semantic correctness, not primarily for memory optimization.

---

# Final Validation

Before exporting the cleaned dataset, I reviewed the result again.

I checked:

- remaining missing values;
- exact duplicates;
- minimum `Quantity`;
- minimum `Price`;
- minimum and maximum dates;
- whether recalculated `Total` still matched `Price × Quantity`;
- final data types.

The final dataset contains:

```text
100 rows
11 columns
0 exact duplicates
0 missing Category values
```

Remaining missing values:

| Column | Missing values |
| --- | ---: |
| `Order_Date` | 1 |
| `Quantity` | 6 |
| `Price` | 7 |
| `Total` | 12 |

These missing values were intentionally preserved because they could not be recovered reliably from the available information.

---

# Before and After

## Raw dataset

```text
103 rows
inconsistent column names
extra whitespace
mixed categorical capitalization
incorrect categorical labels
numeric columns stored as text
malformed numeric values
negative numeric values
incorrect Total values
exact duplicate records
mixed date formats
invalid date value
missing values
inconsistent Product -> Category relationships
```

## Cleaned dataset

```text
100 rows
normalized column names
cleaned string values
normalized categorical values
appropriate pandas dtypes
recoverable numeric values corrected
negative sign errors corrected
Total recalculated from Price × Quantity
exact duplicates removed
Order_Date parsed as datetime
invalid date kept as missing
Category rebuilt from Product mapping
unrecoverable values intentionally left missing
```

---

# What I Intentionally Did Not Do

I did not try to make the dataset look artificially perfect.

In particular, I did not:

- drop every row containing a missing value;
- replace unknown prices with averages;
- guess quantities;
- invent a date for `abc`;
- delete unusual 2023 records only because they looked different;
- remove negative-value rows before investigating them;
- treat repeated IDs as duplicates without comparing the complete records;
- perform a large EDA or business analysis on only 100 cleaned records.

The purpose of the project is the **cleaning process itself**.

---

# Project Structure

```text
ecommerce-data-cleaning/
├── data/
│   ├── raw/
│   │   └── messy_ecommerce_sales_data.csv
│   └── cleaned/
│       └── ecommerce_sales_cleaned.csv
├── src/
│   └── data_cleaning.py
├── README.md
├── requirements.txt
└── .gitignore
```

---

# Tools

- Python
- pandas
- pathlib
- PyCharm
- Git
- GitHub

---

# Running the Project

Create and activate a virtual environment, install the dependencies, and run:

```bash
python src/data_cleaning.py
```

The script reads the raw dataset from:

```text
data/raw/messy_ecommerce_sales_data.csv
```

and exports the cleaned dataset to:

```text
data/cleaned/ecommerce_sales_cleaned.csv
```

---

# Skills Demonstrated

This project demonstrates practical experience with:

- inspecting unfamiliar raw data;
- preserving an untouched raw dataset;
- string cleaning;
- categorical normalization;
- numeric parsing with `pd.to_numeric`;
- distinguishing invalid values from missing values;
- investigating suspicious records before deleting them;
- validating relationships between columns;
- correcting data based on verified rules;
- handling duplicate records;
- mixed datetime parsing;
- working with `NaN` and `NaT`;
- pandas categorical dtype;
- nullable integer dtype;
- `groupby`;
- named aggregation;
- `idxmax`;
- `.loc`;
- `.set_index`;
- `.map`;
- rule-based data restoration;
- final data validation.

---

# Final Result

The project produces a reproducible cleaned e-commerce dataset with **100 records**.

The main result is not a cleaner CSV. The project documents the reasoning behind each decision: what I noticed, what I checked, which assumptions I validated, which values I could restore, and which values I intentionally left unknown.

