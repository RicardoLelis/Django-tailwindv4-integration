#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
sys.path.append('/Users/lelisra/Documents/code/tailwind4-django-how/project')
django.setup()

from app.models import TrainingModule

# Create sample training modules
modules = [
    {
        'title': 'Disability Awareness & Etiquette',
        'description': 'Learn about different types of disabilities and how to interact respectfully with passengers who have accessibility needs.',
        'duration_minutes': 45,
        'is_mandatory': True,
        'order': 1,
        'quiz_questions': [
            {
                'question': 'When assisting a wheelchair user, you should:',
                'options': ['Push their wheelchair without asking', 'Ask before providing assistance', 'Assume they need help', 'Speak louder'],
                'correct': 1
            },
            {
                'question': 'Person-first language means:',
                'options': ['Speaking loudly', 'Saying "person with disability" instead of "disabled person"', 'Using medical terms', 'Avoiding conversation'],
                'correct': 1
            },
            {
                'question': 'Which is the most respectful way to interact with a person who has a visual impairment?',
                'options': ['Speak in a loud voice', 'Identify yourself when approaching', 'Grab their arm to guide them', 'Avoid eye contact'],
                'correct': 1
            }
        ]
    },
    {
        'title': 'Safe Transfer Techniques',
        'description': 'Master safe techniques for assisting passengers with transfers from wheelchairs to vehicle seats.',
        'duration_minutes': 30,
        'is_mandatory': True,
        'order': 2,
        'quiz_questions': [
            {
                'question': 'Before assisting with a transfer, you should:',
                'options': ['Start immediately', 'Ask about their preferred method', 'Use your own technique', 'Rush to save time'],
                'correct': 1
            },
            {
                'question': 'When should you never attempt to lift a passenger?',
                'options': ['When they are heavy', 'When you have not been trained', 'When they ask you not to', 'All of the above'],
                'correct': 3
            }
        ]
    },
    {
        'title': 'Equipment Operation',
        'description': 'Learn to safely operate wheelchair ramps, lifts, and securing systems.',
        'duration_minutes': 30,
        'is_mandatory': True,
        'order': 3,
        'quiz_questions': [
            {
                'question': 'Before deploying a wheelchair ramp, you should:',
                'options': ['Check for obstacles and ensure area is clear', 'Deploy quickly', 'Have passenger wait inside', 'Turn off engine'],
                'correct': 0
            },
            {
                'question': 'How many wheelchair tie-down points are required for safety?',
                'options': ['2', '3', '4', '6'],
                'correct': 2
            }
        ]
    },
    {
        'title': 'Emergency Procedures',
        'description': 'Essential emergency response procedures for accessible transportation.',
        'duration_minutes': 20,
        'is_mandatory': True,
        'order': 4,
        'quiz_questions': [
            {
                'question': 'In an emergency evacuation, your priority is:',
                'options': ['Save yourself first', 'Call emergency services then assist passenger', 'Wait for help', 'Panic'],
                'correct': 1
            },
            {
                'question': 'The emergency contact number in Portugal is:',
                'options': ['911', '999', '112', '115'],
                'correct': 2
            }
        ]
    },
    {
        'title': 'Platform Policies & Procedures',
        'description': 'Understanding RideConnect policies, booking system, and customer service standards.',
        'duration_minutes': 20,
        'is_mandatory': True,
        'order': 5,
        'quiz_questions': [
            {
                'question': 'RideConnect commission rate is:',
                'options': ['15%', '20-25%', '30%', '10%'],
                'correct': 1
            },
            {
                'question': 'What should you do if a passenger has special requirements?',
                'options': ['Ignore them', 'Read the booking notes carefully', 'Cancel the ride', 'Charge extra'],
                'correct': 1
            }
        ]
    },
    {
        'title': 'Advanced Medical Transport',
        'description': 'Optional training for drivers who want to transport passengers with complex medical needs.',
        'duration_minutes': 60,
        'is_mandatory': False,
        'order': 6,
        'quiz_questions': [
            {
                'question': 'When transporting someone with oxygen equipment:',
                'options': ['You can smoke in the vehicle', 'No special precautions needed', 'Ensure proper ventilation and no smoking', 'Turn off the equipment'],
                'correct': 2
            }
        ]
    },
    {
        'title': 'Sign Language Basics',
        'description': 'Learn basic Portuguese sign language for communicating with deaf passengers.',
        'duration_minutes': 90,
        'is_mandatory': False,
        'order': 7,
        'quiz_questions': [
            {
                'question': 'When communicating with a deaf passenger who uses sign language:',
                'options': ['Speak loudly', 'Face them and speak clearly', 'Turn away while talking', 'Use gestures only'],
                'correct': 1
            }
        ]
    }
]

created_count = 0
for module_data in modules:
    module, created = TrainingModule.objects.get_or_create(
        title=module_data['title'],
        defaults=module_data
    )
    if created:
        created_count += 1
        print(f"Created module: {module.title}")
    else:
        print(f"Module already exists: {module.title}")

print(f"\nTotal modules in database: {TrainingModule.objects.count()}")
print(f"Created {created_count} new modules")