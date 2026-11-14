# PROMPT.md

Prompts used with Gemma-3-1B (`google/gemma-3-1b-it`) in Task-1. Each prompt gets a block of 12 numbered requirements pulled from the CIS benchmark PDF, shown here as a placeholder. The code that builds them is in `cisdiff/extractor.py`.

## zero-shot

```
You are a security analyst reading the CIS Docker Benchmark. Below is a numbered list of security requirements. Group them into key data elements (KDEs). A KDE is the Docker component or setting the requirements protect, for example a container user, a base image or the Docker daemon. One KDE can map to several requirements. Every requirement number must appear exactly once.

Answer only in this format, one block per KDE:
KDE: <short name of the element>
REQS: <comma separated requirement numbers>

Requirements:
<numbered CIS requirements, 12 per prompt, e.g.
4.1 Ensure that a user for the container has been created
4.2 Ensure that containers use only trusted base images>
```

## few-shot

```
You are a security analyst reading the CIS Docker Benchmark. Below is a numbered list of security requirements. Group them into key data elements (KDEs). A KDE is the Docker component or setting the requirements protect, for example a container user, a base image or the Docker daemon. One KDE can map to several requirements. Every requirement number must appear exactly once.

Answer only in this format, one block per KDE:
KDE: <short name of the element>
REQS: <comma separated requirement numbers>

Example requirements:
2.1 Run the Docker daemon as a non-root user, if possible
2.2 Ensure network traffic is restricted between containers on the default bridge
2.3 Ensure the logging level is set to 'info'
2.4 Ensure Docker is allowed to make changes to iptables

Example answer:
KDE: Docker daemon user
REQS: 2.1
KDE: Container network
REQS: 2.2, 2.4
KDE: Daemon logging
REQS: 2.3

Requirements:
<numbered CIS requirements, 12 per prompt, e.g.
4.1 Ensure that a user for the container has been created
4.2 Ensure that containers use only trusted base images>
```

## chain-of-thought

```
You are a security analyst reading the CIS Docker Benchmark. Below is a numbered list of security requirements. Group them into key data elements (KDEs). A KDE is the Docker component or setting the requirements protect, for example a container user, a base image or the Docker daemon. One KDE can map to several requirements. Every requirement number must appear exactly once.

Think step by step. First, for each requirement, write one short line naming the Docker component it is about. Second, merge requirements that are about the same component. Third, write the final answer after a line that says ANSWER.

Answer only in this format, one block per KDE:
KDE: <short name of the element>
REQS: <comma separated requirement numbers>

Requirements:
<numbered CIS requirements, 12 per prompt, e.g.
4.1 Ensure that a user for the container has been created
4.2 Ensure that containers use only trusted base images>
```
