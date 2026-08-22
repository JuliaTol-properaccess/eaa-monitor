---
title: "Valt mijn website onder de EAA?"
slug: "valt-mijn-website-onder-de-eaa"
description: "Lang niet elke website valt onder de European Accessibility Act. Check met een paar vragen of de wet voor jouw website geldt, en begrijp de micro-vrijstelling."
answer: "Niet elke website valt onder de European Accessibility Act. De wet geldt voor bedrijven die online producten of diensten aan consumenten verkopen. Ben je een micro-onderneming met minder dan 10 medewerkers en een jaaromzet van maximaal € 2 miljoen, dan ben je waarschijnlijk vrijgesteld. Hieronder check je het met een paar vragen."
date: 2026-06-08
theme: "scope"
keywords:
  - eaa
  - scope
  - micro-vrijstelling
  - website
  - toegankelijkheid
sources:
  - { title: "Ondernemersplein: regels voor digitale toegankelijkheid van producten en diensten", url: "https://ondernemersplein.overheid.nl/european-accessibility-act-producten-en-diensten-moeten-volledig-toegankelijk-zijn/" }
  - { title: "ACM: toegankelijkheid e-commerce en elektronische communicatie", url: "https://www.acm.nl/en/accessibility/accessibility-e-commerce-services-and-electronic-communications-services" }
---

De European Accessibility Act geldt sinds 28 juni 2025. Sindsdien circuleert er veel onjuiste informatie. De meest hardnekkige claim: vanaf die datum zou elke website aan de wet moeten voldoen. Dat klopt niet. Lang niet elke website valt eronder.

Dit artikel legt uit voor wie de wet geldt. Onderaan staat een korte checker waarmee je een eerste indicatie krijgt.

## Waar gaat de EAA over?

De European Accessibility Act harmoniseert de Europese regels voor de toegankelijkheid van bepaalde producten en diensten. E-commerce is een van die diensten. Verkoop je online aan consumenten, dan is de kans groot dat je eronder valt. Dan moeten je website en bestelproces bruikbaar zijn voor mensen met een beperking.

Belangrijk: het doel van de wet is marktharmonisatie binnen Europa. Toegankelijkheid is het middel, niet een losse eis die voor iedereen automatisch geldt. Daarom valt niet elke site eronder.

## De drie vragen die de scope bepalen

Of de wet voor jou geldt, hangt vooral af van drie dingen.

**1. Verkoop je aan consumenten?** De EAA beschermt consumenten. Lever je uitsluitend aan andere bedrijven, dan val je in beginsel buiten de consumentgerichte verplichtingen.

**2. Hoeveel mensen werken er?** Heb je 10 of meer medewerkers, dan tel je niet als micro-onderneming.

**3. Wat is je jaaromzet?** Is je jaaromzet meer dan € 2 miljoen, dan tel je evenmin als micro-onderneming.

## De micro-vrijstelling

Voor dienstverleners kent de wet een vrijstelling voor micro-ondernemingen. Een micro-onderneming heeft minder dan 10 medewerkers en een jaaromzet van maximaal € 2 miljoen. Voldoe je aan beide grenzen, dan ben je als dienstverlener vrijgesteld.

Let op: dit verklaart waarom de meeste websites die nergens bij een keurmerk of vakorganisatie zijn aangesloten, buiten beeld blijven. Dat zijn vaak kleine ondernemingen onder beide grenzen.

> Twijfel je over je cijfers? Reken met de actuele aantallen, niet met een schatting van vorig jaar. Eén medewerker of een paar ton omzet erbij kan het verschil maken tussen vrijgesteld en verplicht.

## Een verklaring is niet hetzelfde als toegankelijk zijn

Veel ondernemers denken dat een toegankelijkheidsverklaring in de footer voldoende is. Een verklaring laat zien dat je je bewust bent van de regels en beschrijft hoe toegankelijk je site is. De echte verplichting is dat je site ook werkt voor mensen met een beperking. De verklaring is het sluitstuk, niet de hele opgave.

Val je onder de wet, dan is de volgende vraag waar je nu staat. In het [overzicht van toegankelijkheidstools](/tools.html) staat waarmee je dat zelf kunt nakijken.

## Check je situatie

Beantwoord de vragen hieronder voor een eerste indicatie. Dit is geen juridisch advies en geen audit, maar het helpt je de scope te begrijpen.

<div class="not-prose my-8 rounded-3xl ring-1 ring-brand-light bg-softblue p-6 md:p-8" id="eaa-checker">
  <form id="eaa-checker-form">
    <fieldset class="border-0 p-0 m-0">
      <legend class="text-lg font-bold text-navy mb-4">Valt jouw website onder de EAA?</legend>

      <div class="mb-5">
        <p class="font-semibold text-navy mb-2">1. Aan wie verkoop je?</p>
        <label class="flex items-center gap-2 mb-1"><input type="radio" name="klant" value="b2c"> Aan consumenten, eventueel ook aan bedrijven</label>
        <label class="flex items-center gap-2"><input type="radio" name="klant" value="b2b"> Uitsluitend aan bedrijven</label>
      </div>

      <div class="mb-5">
        <p class="font-semibold text-navy mb-2">2. Hoeveel medewerkers heb je?</p>
        <label class="flex items-center gap-2 mb-1"><input type="radio" name="medewerkers" value="lt10"> Minder dan 10</label>
        <label class="flex items-center gap-2"><input type="radio" name="medewerkers" value="ge10"> 10 of meer</label>
      </div>

      <div class="mb-6">
        <p class="font-semibold text-navy mb-2">3. Wat is je jaaromzet?</p>
        <label class="flex items-center gap-2 mb-1"><input type="radio" name="omzet" value="le2"> € 2 miljoen of minder</label>
        <label class="flex items-center gap-2"><input type="radio" name="omzet" value="gt2"> Meer dan € 2 miljoen</label>
      </div>

      <button type="submit" class="utrecht-button utrecht-button--primary-action">Toon indicatie</button>
    </fieldset>
  </form>
  <div id="eaa-checker-result" role="status" aria-live="polite" class="mt-6"></div>
</div>

<script>
(function () {
  var form = document.getElementById('eaa-checker-form');
  if (!form) return;
  var out = document.getElementById('eaa-checker-result');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var data = new FormData(form);
    var klant = data.get('klant');
    var medewerkers = data.get('medewerkers');
    var omzet = data.get('omzet');
    if (!klant || !medewerkers || !omzet) {
      out.innerHTML = '<p class="rounded-xl bg-white ring-1 ring-line p-4 text-navy">Beantwoord eerst alle drie de vragen.</p>';
      return;
    }
    var title, body, tone;
    if (klant === 'b2b') {
      tone = 'info';
      title = 'Waarschijnlijk niet';
      body = 'Je verkoopt alleen aan bedrijven. De consumentgerichte verplichtingen van de EAA gelden dan in beginsel niet. Lever je toch ook aan consumenten, kies dan de eerste optie.';
    } else if (medewerkers === 'lt10' && omzet === 'le2') {
      tone = 'info';
      title = 'Mogelijk vrijgesteld';
      body = 'Je hebt minder dan 10 medewerkers en een omzet van maximaal € 2 miljoen. Als dienstverlener val je dan mogelijk onder de micro-vrijstelling. Groei je over een van beide grenzen, dan verandert dat.';
    } else {
      tone = 'warning';
      title = 'Waarschijnlijk wel';
      body = 'Je verkoopt aan consumenten en bent geen micro-onderneming. De kans is groot dat de EAA voor je geldt. Zorg dat je website toegankelijk is en publiceer een toegankelijkheidsverklaring.';
    }
    var cls = tone === 'warning' ? 'notice notice-warning' : 'notice notice-info';
    out.innerHTML = '<div class="' + cls + '"><strong>' + title + '.</strong> ' + body +
      ' <span class="block mt-2 text-sm text-gray-600">Dit is een indicatie, geen juridisch advies. Twijfel je? Laat je situatie toetsen.</span></div>';
  });
})();
</script>

## Kort samengevat

Verkoop je aan consumenten en ben je geen micro-onderneming, dan val je waarschijnlijk onder de EAA. Lever je alleen aan bedrijven, of blijf je onder beide micro-grenzen, dan is de kans groot dat de wet niet voor je geldt. Laat je niet leiden door angst of onjuiste claims, maar check je eigen situatie.
