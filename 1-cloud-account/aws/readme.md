### Get an AWS account

This is the AWS version of [Get the Azure subscription for students](../readme.md). Choose one of the options below.

#### Option A: Personal AWS account (recommended)

**Credit card not required!!!** New accounts get Free Tier credits, and the AWS exercises in this course stay within the Free Tier (or warn you where they don't), but you pay for anything above it.

1. Sign up at: https://aws.amazon.com/free
2. Sign in to the AWS Console as the root user
3. Set up a budget alert so you don't get unexpected charges: https://console.aws.amazon.com/billing/home#/budgets (choose the "Zero spend budget" template)
4. Delete resources after each exercise

#### Option B: AWS Academy Learner Lab

**Credit card not required!!!** Use this option only if the course instructor invited you to an AWS Academy class.

1. Wait for the invitation e-mail from AWS Academy, sent to your school e-mail account by the course instructor
2. Accept the invitation and create your AWS Academy account: https://awsacademy.instructure.com
3. Open the course, go to "Modules" and open the "Learner Lab"
4. Click "Start Lab" and wait until the dot next to "AWS" turns green
5. Click "AWS" to open the AWS Console

Things to know about the Learner Lab:
- A lab session lasts a few hours. When it ends, running EC2 instances are stopped (not deleted) and start again with the next session
- You have a limited credit budget for the whole course. Delete resources after each exercise so you don't run out
- You can usually use only the **US East (N. Virginia)** (`us-east-1`) and **US West (Oregon)** (`us-west-2`) regions. Use `us-east-1` instead of `eu-west-2` in the exercises
- You can't create IAM users or roles. When an exercise creates an IAM role or an instance profile, use the existing `LabRole` role or `LabInstanceProfile` instance profile instead
- Some services aren't available in the Learner Lab. If a command fails with `AccessDenied` or `not authorized`, ask the course instructor
- To use the AWS CLI on your own computer, copy the credentials from "AWS Details" → "AWS CLI" into `~/.aws/credentials`. They change with every lab session. AWS CloudShell in the AWS Console works without this step
