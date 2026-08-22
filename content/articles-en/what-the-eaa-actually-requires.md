---
title: "What the EAA actually requires: an accessible service, not a statement"
slug: "what-the-eaa-actually-requires"
description: "The European Accessibility Act does not require an audit and does not ask for a statement in the Dutch register. It requires an accessible service. Here is what that means in practice, and where the confusion comes from."
date: 2026-08-22
theme: "mythes"
answer: "The EAA requires an accessible website, app or product. It does not oblige you to commission an audit, and the accessibility statement in the Dutch register belongs to a different law, the one covering the public sector. Under the EAA you publish information about the accessibility of your service, for example in your terms and conditions."
keywords:
  - EAA requirements
  - accessibility statement EAA
  - is an accessibility audit mandatory
  - WCAG-EM
sources:
  - { title: "Directive (EU) 2019/882 (European Accessibility Act)", url: "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32019L0882" }
  - { title: "Dutch register of accessibility statements", url: "https://www.toegankelijkheidsverklaring.nl/register" }
---

Two things get mixed up constantly, including by suppliers selling accessibility work. Sorting them out saves money and prevents a false sense of compliance.

## What the law asks of you

The European Accessibility Act requires an accessible website, app or product. That is the obligation.

It does not require you to commission an investigation. An audit is the way to find out where you stand, not a legal duty in itself. Anyone telling you that the EAA makes an audit mandatory is selling something.

What the EAA does require is that you publish information about the accessibility of your service, for example in your general terms and conditions. If your service does not meet the requirements, the Dutch duty to report applies as well: you notify the regulator yourself and publish an accessibility statement in a place that is easy to find.

## The register is a different law

The [Dutch register of accessibility statements](https://www.toegankelijkheidsverklaring.nl/register) belongs to the Besluit digitale toegankelijkheid overheid, the regime for government bodies and bodies governed by public law. That is where the familiar rules come from: every digital channel needs its own statement, there are five status levels, and every investigation has to follow WCAG-EM.

None of that applies to a commercial company under the EAA. If you have read that the EAA requires a statement per channel, you have read a description of the other law.

There is one thing worth borrowing from that regime anyway. The register only accepts research carried out following WCAG-EM, and a report expires after 36 months. Those are reasonable benchmarks for quality and shelf life even when they do not bind you.

## Why a scan is not enough either

An automated scan recognises roughly 30% of the checkpoints under WCAG. That figure is an estimate from the field rather than a measurement, so treat it as an order of magnitude.

What a tool can measure is what is measurable: a missing alt attribute, a contrast ratio below 4.5:1, a button without an accessible name. What no tool judges is meaning. Whether that alt text matches the image. Whether the order a screen reader reads in makes sense. Whether you can get back out of a dialog with the keyboard. Whether an error message is announced at the moment it appears.

Zero errors in a scan is therefore not evidence of anything much. The [tools overview](/tools.html) on this site lists what each tool finds and, more usefully, what it does not.

## What this means in practice

Start with the paths that matter. For a shop that is the entire checkout process, from basket to payment, which is also the path the ACM walks when it tests.

Test with a keyboard alone, with a screen reader, and at 200% zoom. Then decide whether you need an external investigation. You often will, because the parts a tool cannot judge are the parts that stop people from buying, but that decision belongs to you rather than to a supplier's compliance story.

## Where the monitor fits

This site measures weekly whether Dutch organisations publish an accessibility statement in their footer, across seven sectors. That measurement says something about awareness and about the paper trail. It says nothing about whether a site is actually usable.

A statement is the end of the work, not the start of it.
