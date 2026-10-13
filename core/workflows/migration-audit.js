export const meta = {
  name: 'migration-audit',
  description: 'Read-only: assess every module for a migration in parallel, verify the risky claims, and propose a slice order',
  phases: [
    { title: 'Inventory', detail: 'List modules and count the pattern being migrated' },
    { title: 'Assess', detail: 'One read-only agent per module' },
    { title: 'Verify', detail: 'Check each module flagged high-risk or blocked' },
    { title: 'Order', detail: 'Turn the assessments into a slice order' },
  ],
}

// Input: a string such as "Combine to async/await" or an object { migration, scope }.
const migration = typeof args === 'string' ? args : args && args.migration
const scope = (args && typeof args === 'object' && args.scope) || 'the whole repository'
if (!migration) {
  return { error: 'Say what to migrate, for example: /mobile-core:migration-audit Combine to async/await' }
}

const READ_ONLY = 'This is a read-only assessment. Do not edit, create or delete files, do not run builds, and do not use git to change anything.'

const INVENTORY_SCHEMA = {
  type: 'object',
  required: ['modules'],
  properties: {
    modules: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'path', 'occurrences'],
        properties: {
          name: { type: 'string' },
          path: { type: 'string' },
          occurrences: { type: 'integer' },
          dependsOn: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}

const ASSESSMENT_SCHEMA = {
  type: 'object',
  required: ['module', 'risk', 'effort', 'summary'],
  properties: {
    module: { type: 'string' },
    occurrences: { type: 'integer' },
    risk: { type: 'string', enum: ['low', 'medium', 'high', 'blocked'] },
    effort: { type: 'string', enum: ['small', 'medium', 'large'] },
    summary: { type: 'string' },
    testCoverage: { type: 'string' },
    prerequisites: { type: 'array', items: { type: 'string' } },
    hazards: { type: 'array', items: { type: 'string' } },
    evidence: { type: 'array', items: { type: 'string' } },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['confirmed', 'risk', 'reason'],
  properties: {
    confirmed: { type: 'boolean' },
    risk: { type: 'string', enum: ['low', 'medium', 'high', 'blocked'] },
    reason: { type: 'string' },
  },
}

phase('Inventory')
const inventory = await agent(
  `${READ_ONLY}\n\nMigration under consideration: ${migration}. Scope: ${scope}.\n\n` +
    'Run `mobile recon` and `mobile detect`. Then list the modules, targets or top-level feature folders in scope ' +
    '(from the build definition, not from guesswork). For each give its path, the number of occurrences of the ' +
    'pattern being migrated away from (use an exact search for the specific APIs), and the other listed modules it depends on. ' +
    'Leave out modules with zero occurrences.',
  { label: 'inventory', phase: 'Inventory', schema: INVENTORY_SCHEMA },
)

const modules = ((inventory && inventory.modules) || []).filter(m => m.occurrences > 0).slice(0, 60)
if (modules.length === 0) {
  return { migration, scope, modules: [], note: 'No module contains the pattern being migrated. Nothing to plan.' }
}
log(`${modules.length} modules contain the old pattern`)

const assessed = await pipeline(
  modules,
  m =>
    agent(
      `${READ_ONLY}\n\nMigration: ${migration}. Assess the module "${m.name}" at ${m.path} ` +
        `(${m.occurrences} occurrences of the old pattern).\n\n` +
        'Load the platform skill for this code (mobile-ios:ios, mobile-android:android or mobile-flutter:flutter) and read its legacy.md. ' +
        'Read the files with the most occurrences and the tests that cover them. Report: how risky it is to migrate this module and why; ' +
        'how much work; what test coverage pins the current behaviour; what must exist first (adapters, seams, version upgrades, ' +
        'characterization tests); the specific hazards (lifecycle, threading, error or cancellation semantics that differ between old and new; ' +
        'public API other modules call; persistence; anything reached by reflection or by name). ' +
        'Use "blocked" only when the module cannot be migrated until something outside it changes. Cite file:line for every hazard in "evidence".',
      { label: `assess:${m.name}`, phase: 'Assess', schema: ASSESSMENT_SCHEMA },
    ),
  assessment => {
    if (!assessment || (assessment.risk !== 'high' && assessment.risk !== 'blocked')) return assessment
    return agent(
      `${READ_ONLY}\n\nAnother engineer assessed the module "${assessment.module}" for the migration "${migration}" as ` +
        `${assessment.risk} risk. Their hazards: ${JSON.stringify(assessment.hazards || [])}. Their evidence: ` +
        `${JSON.stringify(assessment.evidence || [])}.\n\nCheck each claim against the code. Try to show the rating is too high: ` +
        'is the hazard real and reachable, or is it handled already? Answer with the rating you can defend and the reason.',
      { label: `verify:${assessment.module}`, phase: 'Verify', schema: VERDICT_SCHEMA },
    ).then(verdict => (verdict ? { ...assessment, risk: verdict.risk, verified: verdict } : assessment))
  },
)

const assessments = assessed.filter(Boolean)

phase('Order')
const plan = await agent(
  `${READ_ONLY}\n\nMigration: ${migration}. Scope: ${scope}.\n\nModule inventory with dependencies:\n${JSON.stringify(modules)}\n\n` +
    `Per-module assessments:\n${JSON.stringify(assessments)}\n\n` +
    'Follow the mobile-core:migrate skill. Produce a migration plan in the structure of its references/plan-template.md: ' +
    'baseline table, coexistence and freeze rules, and an ordered list of slices (enablers first, leaves before trunks, one risk per slice, ' +
    'each slice one reviewable pull request). Put blocked modules last with what unblocks them. Do not write any file: return the plan as Markdown.',
  { label: 'plan', phase: 'Order' },
)

return { migration, scope, modules: modules.length, assessments, plan }
